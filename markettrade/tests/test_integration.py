import json
import os
import tempfile
from functools import partial

from app.config import Config, PriceSanityConfig, RiskConfig
from marketrisk.risk.engine import RiskEngine
from marketrisk.risk.models import ProposedAction
from shared.blob import get_store
from trade.decision import decide
from trade.models import SignalEvent
from trade.validation import ValidationPipeline, validate_price_sanity, validate_schema


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
    return SignalEvent(**base)


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


def _make_pipeline(config):
    return ValidationPipeline([
        validate_schema,
        partial(
            validate_price_sanity,
            enabled=config.price_sanity.ENABLED,
            min_price=config.price_sanity.MIN_PRICE,
            max_price=config.price_sanity.MAX_PRICE,
        ),
    ])


def _run_validated_pipeline(payload, config, risk_engine, store):
    """Like _run_pipeline but starts from a raw dict, running validation first."""
    pipeline = _make_pipeline(config)
    vresult = pipeline.run(payload)
    if not vresult.valid:
        return {"rejected": True, "stage": "validation", "reason": vresult.reason}
    return _run_pipeline(vresult.event, config, risk_engine, store)


class TestValidationPipelineIntegration:
    def test_invalid_schema_never_reaches_decide(self):
        config = _config()
        engine = RiskEngine(config.risk)

        with tempfile.TemporaryDirectory() as tmpdir:
            store = get_store("disk", tmpdir)
            payload = {"type": "LARGE_TRADE", "cluster_id": 2, "anomaly_score": 0.9,
                        "price": "42000.0", "quantity": "100.0"}
            # missing "symbol"
            result = _run_validated_pipeline(payload, config, engine, store)

            assert result["rejected"] is True
            assert result["stage"] == "validation"
            assert result["reason"] == "symbol"
            assert _read_all_records(tmpdir) == []

    def test_insane_price_never_reaches_decide(self):
        config = _config()
        config.price_sanity = PriceSanityConfig(
            ENABLED=True, MIN_PRICE=1.0, MAX_PRICE=100000.0,
        )
        engine = RiskEngine(config.risk)

        with tempfile.TemporaryDirectory() as tmpdir:
            store = get_store("disk", tmpdir)
            payload = {"symbol": "BTCUSDT", "type": "LARGE_TRADE", "cluster_id": 2,
                        "anomaly_score": 0.9, "price": "999999999.0", "quantity": "100.0"}
            result = _run_validated_pipeline(payload, config, engine, store)

            assert result["rejected"] is True
            assert result["reason"] == "price_out_of_range"
            assert _read_all_records(tmpdir) == []

    def test_valid_event_reaches_decide(self):
        config = _config(risk_overrides={"MAX_TRADE_QUANTITY": 500.0, "MAX_SYMBOL_EXPOSURE": 5000.0})
        engine = RiskEngine(config.risk)

        with tempfile.TemporaryDirectory() as tmpdir:
            store = get_store("disk", tmpdir)
            payload = {"symbol": "BTCUSDT", "type": "LARGE_TRADE", "cluster_id": 2,
                        "anomaly_score": 0.9, "price": "42000.0", "quantity": "100.0"}
            result = _run_validated_pipeline(payload, config, engine, store)

            assert result is not None
            assert result.get("rejected") is not True
            assert result["risk_approved"] is True

    def test_schema_failure_before_price_failure(self):
        """Payload that fails both schema AND price: rejection reason is schema."""
        config = _config()
        config.price_sanity = PriceSanityConfig(
            ENABLED=True, MIN_PRICE=1.0, MAX_PRICE=100000.0,
        )
        engine = RiskEngine(config.risk)

        with tempfile.TemporaryDirectory() as tmpdir:
            store = get_store("disk", tmpdir)
            # missing symbol (schema fail) AND insane price (price_sanity fail)
            payload = {"type": "LARGE_TRADE", "cluster_id": 2,
                        "anomaly_score": 0.9, "price": "999999999.0", "quantity": "100.0"}
            result = _run_validated_pipeline(payload, config, engine, store)

            assert result["rejected"] is True
            assert result["reason"] == "symbol"  # schema caught first
