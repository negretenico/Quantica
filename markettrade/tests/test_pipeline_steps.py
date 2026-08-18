from unittest.mock import MagicMock, patch

from trade.models import SignalEvent
from trade.pipeline.context import PipelineContext


def _payload(**overrides):
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


def _event(**overrides):
    base = {
        "symbol": "BTCUSDT",
        "type": "LARGE_TRADE",
        "cluster_id": 2,
        "anomaly_score": 0.9,
        "price": 42000.0,
        "quantity": 100.0,
    }
    base.update(overrides)
    return SignalEvent(**base)


def _unenriched_event(**overrides):
    base = {
        "symbol": "BTCUSDT",
        "type": "LARGE_TRADE",
        "price": 42000.0,
        "quantity": 100.0,
    }
    base.update(overrides)
    return SignalEvent(**base)


class TestDedupStep:
    def test_unique_event_passes(self):
        from trade.pipeline.steps.dedup import DedupStep

        dedup = MagicMock()
        dedup.is_duplicate.return_value = False
        step = DedupStep(dedup)
        ctx = PipelineContext(payload=_payload())
        assert step.execute(ctx) is True

    def test_duplicate_event_halts(self):
        from trade.pipeline.steps.dedup import DedupStep

        dedup = MagicMock()
        dedup.is_duplicate.return_value = True
        step = DedupStep(dedup)
        ctx = PipelineContext(payload=_payload())
        assert step.execute(ctx) is False


class TestValidateStep:
    def test_valid_payload_sets_event(self):
        from trade.pipeline.steps.validate import ValidateStep
        from trade.validation import ValidationPipeline, validate_schema

        vp = ValidationPipeline([validate_schema])
        step = ValidateStep(vp)
        ctx = PipelineContext(payload=_payload())
        assert step.execute(ctx) is True
        assert ctx.event is not None
        assert ctx.event.symbol == "BTCUSDT"

    def test_invalid_payload_halts(self):
        from trade.pipeline.steps.validate import ValidateStep
        from trade.validation import ValidationPipeline, validate_schema

        vp = ValidationPipeline([validate_schema])
        step = ValidateStep(vp)
        ctx = PipelineContext(payload={"type": "LARGE_TRADE"})  # missing symbol
        assert step.execute(ctx) is False
        assert ctx.event is None

    def test_price_cache_recorded(self):
        from trade.pipeline.steps.validate import ValidateStep
        from trade.validation import ValidationPipeline, validate_schema

        cache = MagicMock()
        vp = ValidationPipeline([validate_schema])
        step = ValidateStep(vp, price_cache=cache)
        ctx = PipelineContext(payload=_payload(eventTime=1700000000000))
        step.execute(ctx)
        cache.record.assert_called_once()


class TestDecideStep:
    def test_actionable_signal_passes(self):
        from trade.pipeline.steps.decide import DecideStep
        from app.config import Config

        config = Config()
        step = DecideStep(config)
        ctx = PipelineContext(payload=_payload())
        ctx.event = _event()
        assert step.execute(ctx) is True
        assert ctx.decision is not None
        assert ctx.decision["action"] != "HOLD"

    def test_hold_signal_halts(self):
        from trade.pipeline.steps.decide import DecideStep
        from app.config import Config

        config = Config()
        step = DecideStep(config)
        ctx = PipelineContext(payload=_payload())
        ctx.event = _event(anomaly_score=0.1)  # below threshold → HOLD
        assert step.execute(ctx) is False
        assert ctx.decision["action"] == "HOLD"

    def test_rate_limited_halts(self):
        from trade.pipeline.steps.decide import DecideStep
        from app.config import Config

        rate_limiter = MagicMock()
        rate_limiter.check.return_value = (False, "max_per_minute exceeded")
        rate_limiter._windows = {"BTCUSDT": [1, 2, 3]}
        rate_limiter._max = 10
        config = Config()
        step = DecideStep(config, rate_limiter=rate_limiter)
        ctx = PipelineContext(payload=_payload())
        ctx.event = _event()
        assert step.execute(ctx) is False


class TestRiskEvaluateStep:
    def test_sets_risk_decision(self):
        from trade.pipeline.steps.risk_evaluate import RiskEvaluateStep
        from app.config import Config

        config = Config()
        engine = MagicMock()
        engine.evaluate.return_value = MagicMock(approved=True, sized_quantity=100.0)
        step = RiskEvaluateStep(engine, config)
        ctx = PipelineContext(payload=_payload())
        ctx.decision = {
            "symbol": "BTCUSDT", "action": "BUY",
            "entry_price": 42000.0, "raw_quantity": 100.0,
        }
        assert step.execute(ctx) is True
        assert ctx.risk_decision is not None
        assert ctx.risk_decision.approved is True


class TestRiskGateStep:
    def test_approved_passes(self):
        from trade.pipeline.steps.risk_gate import RiskGateStep

        step = RiskGateStep()
        ctx = PipelineContext(payload=_payload())
        ctx.decision = {"symbol": "BTCUSDT", "action": "BUY"}
        ctx.risk_decision = MagicMock(approved=True, sized_quantity=100.0)
        assert step.execute(ctx) is True
        assert ctx.decision["risk_approved"] is True
        assert ctx.decision["sized_quantity"] == 100.0

    def test_rejected_halts(self):
        from trade.pipeline.steps.risk_gate import RiskGateStep

        step = RiskGateStep()
        ctx = PipelineContext(payload=_payload())
        ctx.decision = {"symbol": "BTCUSDT", "action": "BUY"}
        ctx.risk_decision = MagicMock(approved=False, rejection_reason="EXCEEDS_TRADE_CAP")
        assert step.execute(ctx) is False


class TestRecordOutcomeStep:
    def test_records_and_schedules(self):
        from trade.pipeline.steps.record_outcome import RecordOutcomeStep

        log = MagicMock()
        lookback = MagicMock()
        step = RecordOutcomeStep(log, lookback)
        decision = {"symbol": "BTCUSDT", "action": "BUY"}
        ctx = PipelineContext(payload=_payload())
        ctx.decision = decision
        assert step.execute(ctx) is True
        log.record.assert_called_once_with(decision)
        lookback.schedule.assert_called_once_with(decision)

    def test_continues_on_record_error(self):
        from trade.pipeline.steps.record_outcome import RecordOutcomeStep

        log = MagicMock()
        log.record.side_effect = RuntimeError("disk full")
        step = RecordOutcomeStep(log)
        ctx = PipelineContext(payload=_payload())
        ctx.decision = {"symbol": "BTCUSDT", "action": "BUY"}
        assert step.execute(ctx) is True  # does not halt


class TestPersistAndNotifyStep:
    def test_writes_and_notifies(self):
        from trade.pipeline.steps.persist_and_notify import PersistAndNotifyStep

        store = MagicMock()
        publisher = MagicMock()
        step = PersistAndNotifyStep(store, publisher)
        decision = {"symbol": "BTCUSDT", "action": "BUY"}
        ctx = PipelineContext(payload=_payload())
        ctx.decision = decision
        assert step.execute(ctx) is True
        store.write.assert_called_once_with(decision)
        publisher.publish.assert_called_once()

    def test_store_failure_raises(self):
        from trade.pipeline.steps.persist_and_notify import PersistAndNotifyStep
        import pytest

        store = MagicMock()
        store.write.side_effect = RuntimeError("write failed")
        publisher = MagicMock()
        step = PersistAndNotifyStep(store, publisher)
        ctx = PipelineContext(payload=_payload())
        ctx.decision = {"symbol": "BTCUSDT", "action": "BUY"}
        with pytest.raises(RuntimeError):
            step.execute(ctx)


class TestNearLimitStep:
    def test_processes_alerts_and_continues(self):
        from trade.pipeline.steps.near_limit import NearLimitStep

        observer_pipeline = MagicMock()
        observer_pipeline.check.return_value = []
        near_limit_obs = MagicMock()
        near_limit_obs.active_symbols.return_value = set()
        risk_alert_store = MagicMock()
        config = MagicMock()
        config.risk.MAX_SYMBOL_EXPOSURE = 5000.0
        risk_engine = MagicMock()
        risk_engine.get_symbol_exposure.return_value = 1000.0

        step = NearLimitStep(observer_pipeline, near_limit_obs, risk_alert_store, config, risk_engine)
        ctx = PipelineContext(payload=_payload())
        ctx.decision = {"symbol": "BTCUSDT", "action": "BUY"}
        ctx.risk_decision = MagicMock(approved=True)
        assert step.execute(ctx) is True
        observer_pipeline.check.assert_called_once()
