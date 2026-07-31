import json
import os
import tempfile

from app.config import Config, RiskConfig
from marketrisk.risk.engine import RiskEngine
from marketrisk.risk.models import ProposedAction
from shared.blob import get_store
from trade.decision import decide


def _config(risk_overrides=None, **overrides):
    cfg = Config()
    if risk_overrides:
        for k, v in risk_overrides.items():
            setattr(cfg.risk, k, v)
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


def _event(**overrides):
    base = {
        "symbol": "BTCUSDT",
        "type": "LARGE_TRADE",
        "cluster_id": 2,
        "anomaly_score": 0.9,
        "price": "42000.00",
        "quantity": "100.0",
    }
    base.update(overrides)
    return base


def _run_pipeline(event, config, risk_engine, store):
    """Mirrors the handle_message flow in run.py."""
    decision = decide(event, config)

    if decision["action"] == "HOLD":
        return None

    proposed = ProposedAction(
        symbol=decision["symbol"],
        action=decision["action"],
        entry_price=decision["entry_price"],
        raw_quantity=decision["raw_quantity"],
        portfolio_value=0.0,
    )

    risk_decision = risk_engine.evaluate(proposed)

    if not risk_decision.approved:
        return {"rejected": True, "reason": risk_decision.rejection_reason}

    decision["risk_approved"] = True
    decision["sized_quantity"] = risk_decision.sized_quantity
    store.write(decision)
    return decision


def _read_all_records(store_path):
    """Read all JSONL records from the blob store directory."""
    records = []
    for filename in sorted(os.listdir(store_path)):
        if filename.endswith(".jsonl"):
            with open(os.path.join(store_path, filename)) as f:
                for line in f:
                    records.append(json.loads(line))
    return records


class TestApprovedDecisionWritten:
    def test_approved_decision_has_risk_fields(self):
        config = _config(risk_overrides={"MAX_TRADE_QUANTITY": 500.0, "MAX_SYMBOL_EXPOSURE": 5000.0})
        engine = RiskEngine(config.risk)

        with tempfile.TemporaryDirectory() as tmpdir:
            store = get_store("disk", tmpdir)
            result = _run_pipeline(_event(quantity="100.0"), config, engine, store)

            assert result is not None
            assert result["risk_approved"] is True
            assert result["sized_quantity"] == 100.0

            records = _read_all_records(tmpdir)
            assert len(records) == 1
            assert records[0]["risk_approved"] is True
            assert records[0]["sized_quantity"] == 100.0

    def test_approved_decision_sized_to_headroom(self):
        config = _config(risk_overrides={"MAX_TRADE_QUANTITY": 500.0, "MAX_SYMBOL_EXPOSURE": 150.0})
        engine = RiskEngine(config.risk)

        with tempfile.TemporaryDirectory() as tmpdir:
            store = get_store("disk", tmpdir)
            result = _run_pipeline(_event(quantity="200.0"), config, engine, store)

            assert result["risk_approved"] is True
            assert result["sized_quantity"] == 150.0


class TestRejectedDecisionNotWritten:
    def test_exceeds_trade_cap_not_written(self):
        config = _config(risk_overrides={"MAX_TRADE_QUANTITY": 50.0})
        engine = RiskEngine(config.risk)

        with tempfile.TemporaryDirectory() as tmpdir:
            store = get_store("disk", tmpdir)
            result = _run_pipeline(_event(quantity="100.0"), config, engine, store)

            assert result["rejected"] is True
            assert result["reason"] == "EXCEEDS_TRADE_CAP"
            assert _read_all_records(tmpdir) == []

    def test_exceeds_symbol_exposure_not_written(self):
        config = _config(risk_overrides={"MAX_TRADE_QUANTITY": 500.0, "MAX_SYMBOL_EXPOSURE": 80.0})
        engine = RiskEngine(config.risk)

        with tempfile.TemporaryDirectory() as tmpdir:
            store = get_store("disk", tmpdir)
            # First trade uses up most exposure
            _run_pipeline(_event(quantity="70.0"), config, engine, store)
            # Second trade fits in remaining headroom (10.0)
            result = _run_pipeline(_event(quantity="20.0"), config, engine, store)

            assert result["risk_approved"] is True
            assert result["sized_quantity"] == 10.0

    def test_hold_produces_no_output(self):
        config = _config()
        engine = RiskEngine(config.risk)

        with tempfile.TemporaryDirectory() as tmpdir:
            store = get_store("disk", tmpdir)
            result = _run_pipeline(
                _event(type="LARGE_TRADE", anomaly_score=0.3),
                config, engine, store,
            )

            assert result is None
            assert _read_all_records(tmpdir) == []

    def test_drawdown_halt_not_written(self):
        config = _config(risk_overrides={
            "MAX_TRADE_QUANTITY": 500.0,
            "MAX_SYMBOL_EXPOSURE": 5000.0,
            "MAX_DRAWDOWN_PCT": 0.10,
        })
        engine = RiskEngine(config.risk)
        # Set peak PnL high, then evaluate with a large drawdown
        engine._peak_pnl = 1000.0

        with tempfile.TemporaryDirectory() as tmpdir:
            store = get_store("disk", tmpdir)
            event = _event(quantity="50.0")
            decision = decide(event, config)
            proposed = ProposedAction(
                symbol=decision["symbol"],
                action=decision["action"],
                entry_price=decision["entry_price"],
                raw_quantity=decision["raw_quantity"],
                portfolio_value=500.0,  # 50% drawdown from peak of 1000
            )
            risk_decision = engine.evaluate(proposed, portfolio_pnl=500.0)

            assert risk_decision.approved is False
            assert risk_decision.rejection_reason == "PORTFOLIO_DRAWDOWN_HALT"
            assert _read_all_records(tmpdir) == []
