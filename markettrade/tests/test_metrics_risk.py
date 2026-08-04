import pytest
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

from marketrisk.app.config import Config as RiskConfig
from marketrisk.risk.engine import RiskEngine
from marketrisk.risk.models import ProposedAction


def _engine(**overrides):
    cfg = RiskConfig(**overrides)
    return RiskEngine(cfg)


def _proposed(symbol="BTCUSDT", quantity=100.0):
    return ProposedAction(
        symbol=symbol,
        action="BUY",
        entry_price=42000.0,
        raw_quantity=quantity,
        portfolio_value=0.0,
    )


@pytest.fixture()
def metrics():
    """Create isolated metrics in a fresh registry for each test."""
    registry = CollectorRegistry()
    m = type("Metrics", (), {})()
    m.risk_evaluations_total = Counter(
        "markettrade_risk_evaluations_total",
        "Total risk evaluations by result",
        ["result"],
        registry=registry,
    )
    m.risk_sized_quantity = Histogram(
        "markettrade_risk_sized_quantity",
        "Sized quantity of approved trades after risk adjustment",
        buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000),
        registry=registry,
    )
    m.risk_exposure_ratio = Gauge(
        "markettrade_risk_exposure_ratio",
        "Current symbol exposure as ratio of max allowed",
        ["symbol"],
        registry=registry,
    )
    return m


def _observe(metrics, risk_decision, symbol, risk_engine, max_exposure):
    """Mirrors observe_risk_evaluation but uses test-local metrics."""
    result_label = "approved" if risk_decision.approved else "rejected"
    metrics.risk_evaluations_total.labels(result=result_label).inc()

    if risk_decision.approved:
        metrics.risk_sized_quantity.observe(risk_decision.sized_quantity)
        exposure = risk_engine.get_symbol_exposure(symbol)
        metrics.risk_exposure_ratio.labels(symbol=symbol).set(exposure / max_exposure)


class TestRiskEvaluationsTotal:
    def test_approved_increments_counter(self, metrics):
        engine = _engine(MAX_TRADE_QUANTITY=500.0, MAX_SYMBOL_EXPOSURE=5000.0)
        decision = engine.evaluate(_proposed(quantity=100.0))

        _observe(metrics, decision, "BTCUSDT", engine, 5000.0)

        assert metrics.risk_evaluations_total.labels(result="approved")._value.get() == 1

    def test_rejected_increments_counter(self, metrics):
        engine = _engine(MAX_TRADE_QUANTITY=50.0)
        decision = engine.evaluate(_proposed(quantity=100.0))

        _observe(metrics, decision, "BTCUSDT", engine, 5000.0)

        assert metrics.risk_evaluations_total.labels(result="rejected")._value.get() == 1


class TestRiskRejectionsByReason:
    def test_exceeds_trade_cap(self):
        engine = _engine(MAX_TRADE_QUANTITY=50.0)
        decision = engine.evaluate(_proposed(quantity=100.0))

        assert decision.rejection_reason == "EXCEEDS_TRADE_CAP"

    def test_exceeds_symbol_exposure(self):
        engine = _engine(MAX_TRADE_QUANTITY=500.0, MAX_SYMBOL_EXPOSURE=80.0)
        engine.evaluate(_proposed(quantity=80.0))
        decision = engine.evaluate(_proposed(quantity=50.0))

        assert decision.rejection_reason == "EXCEEDS_SYMBOL_EXPOSURE"

    def test_portfolio_drawdown_halt(self):
        engine = _engine(MAX_TRADE_QUANTITY=500.0, MAX_SYMBOL_EXPOSURE=5000.0, MAX_DRAWDOWN_PCT=0.10)
        engine._peak_pnl = 1000.0
        decision = engine.evaluate(_proposed(quantity=50.0), portfolio_pnl=500.0)

        assert decision.rejection_reason == "PORTFOLIO_DRAWDOWN_HALT"


class TestRiskSizedQuantity:
    def test_histogram_observes_approved_quantity(self, metrics):
        engine = _engine(MAX_TRADE_QUANTITY=500.0, MAX_SYMBOL_EXPOSURE=5000.0)
        decision = engine.evaluate(_proposed(quantity=100.0))

        _observe(metrics, decision, "BTCUSDT", engine, 5000.0)

        samples = metrics.risk_sized_quantity.collect()[0].samples
        sum_sample = [s for s in samples if s.name.endswith("_sum")]
        assert len(sum_sample) == 1
        assert sum_sample[0].value == 100.0

    def test_histogram_not_observed_on_rejection(self, metrics):
        engine = _engine(MAX_TRADE_QUANTITY=50.0)
        decision = engine.evaluate(_proposed(quantity=100.0))

        _observe(metrics, decision, "BTCUSDT", engine, 5000.0)

        samples = metrics.risk_sized_quantity.collect()[0].samples
        sum_sample = [s for s in samples if s.name.endswith("_sum")]
        assert len(sum_sample) == 1
        assert sum_sample[0].value == 0.0


class TestRiskExposureRatio:
    def test_gauge_set_on_approval(self, metrics):
        engine = _engine(MAX_TRADE_QUANTITY=500.0, MAX_SYMBOL_EXPOSURE=1000.0)
        decision = engine.evaluate(_proposed(symbol="ETHUSDT", quantity=250.0))

        _observe(metrics, decision, "ETHUSDT", engine, 1000.0)

        assert metrics.risk_exposure_ratio.labels(symbol="ETHUSDT")._value.get() == 0.25

    def test_gauge_accumulates_across_trades(self, metrics):
        engine = _engine(MAX_TRADE_QUANTITY=500.0, MAX_SYMBOL_EXPOSURE=1000.0)

        d1 = engine.evaluate(_proposed(symbol="BTCUSDT", quantity=200.0))
        _observe(metrics, d1, "BTCUSDT", engine, 1000.0)

        d2 = engine.evaluate(_proposed(symbol="BTCUSDT", quantity=300.0))
        _observe(metrics, d2, "BTCUSDT", engine, 1000.0)

        assert metrics.risk_exposure_ratio.labels(symbol="BTCUSDT")._value.get() == 0.5

    def test_gauge_not_set_on_rejection(self, metrics):
        engine = _engine(MAX_TRADE_QUANTITY=50.0)
        decision = engine.evaluate(_proposed(quantity=100.0))

        _observe(metrics, decision, "BTCUSDT", engine, 5000.0)

        samples = metrics.risk_exposure_ratio.collect()[0].samples
        btc_samples = [s for s in samples if s.labels.get("symbol") == "BTCUSDT"]
        assert len(btc_samples) == 0
