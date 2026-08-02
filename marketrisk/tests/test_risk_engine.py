import pytest

from marketrisk.app.config import Config
from marketrisk.risk.models import ProposedAction
from marketrisk.risk.engine import RiskEngine


def _make_action(symbol: str = "AAPL", raw_quantity: float = 100.0) -> ProposedAction:
    return ProposedAction(
        symbol=symbol,
        action="BUY",
        entry_price=150.0,
        raw_quantity=raw_quantity,
        portfolio_value=100_000.0,
    )


def _make_engine(max_trade: float = 500.0, max_symbol: float = 1000.0, max_drawdown: float = 0.20) -> RiskEngine:
    config = Config()
    config.MAX_TRADE_QUANTITY = max_trade
    config.MAX_SYMBOL_EXPOSURE = max_symbol
    config.MAX_DRAWDOWN_PCT = max_drawdown
    return RiskEngine(config)


class TestDrawdownHalt:
    def test_no_halt_below_threshold(self):
        engine = _make_engine(max_drawdown=0.50)
        # peak = 2000, current = 1500 → drawdown = 25% < 50%
        engine.evaluate(_make_action(), portfolio_pnl=2000.0)
        decision = engine.evaluate(_make_action(), portfolio_pnl=1500.0)

        assert decision.approved is True
        assert decision.rejection_reason is None

    def test_halt_triggered_at_threshold(self):
        engine = _make_engine(max_drawdown=0.20)
        # peak = 1000, current = 700 → drawdown = 30% > 20%
        engine.evaluate(_make_action(), portfolio_pnl=1000.0)
        decision = engine.evaluate(_make_action(), portfolio_pnl=700.0)

        assert decision.approved is False
        assert decision.sized_quantity is None
        assert decision.rejection_reason == "PORTFOLIO_DRAWDOWN_HALT"

    def test_halt_clears_when_pnl_recovers_above_peak(self):
        engine = _make_engine(max_drawdown=0.20)
        # trigger halt
        engine.evaluate(_make_action(), portfolio_pnl=1000.0)
        engine.evaluate(_make_action(), portfolio_pnl=700.0)
        # recover above old peak → drawdown = 0%
        decision = engine.evaluate(_make_action(), portfolio_pnl=1500.0)

        assert decision.approved is True
        assert decision.rejection_reason is None

    def test_zero_peak_no_halt(self):
        engine = _make_engine(max_drawdown=0.20)
        # first call ever, pnl negative — peak stays 0, drawdown guard returns 0
        decision = engine.evaluate(_make_action(), portfolio_pnl=-500.0)

        assert decision.approved is True

    def test_drawdown_check_before_trade_cap(self):
        """A halted portfolio rejects even a trade that would otherwise pass all caps."""
        engine = _make_engine(max_trade=500.0, max_drawdown=0.20)
        engine.evaluate(_make_action(), portfolio_pnl=1000.0)
        # trigger drawdown
        decision = engine.evaluate(_make_action(raw_quantity=100.0), portfolio_pnl=700.0)

        assert decision.rejection_reason == "PORTFOLIO_DRAWDOWN_HALT"


class TestRiskEngineApproved:
    def test_approved_full_quantity(self):
        engine = _make_engine(max_trade=500.0, max_symbol=1000.0)
        decision = engine.evaluate(_make_action(raw_quantity=100.0))

        assert decision.approved is True
        assert decision.sized_quantity == pytest.approx(100.0)
        assert decision.rejection_reason is None

    def test_approved_capped_to_headroom(self):
        engine = _make_engine(max_trade=1000.0, max_symbol=1000.0)
        # consume 900 of 1000 headroom
        engine.evaluate(_make_action(raw_quantity=900.0))
        # next trade requests 200 but only 100 remains
        decision = engine.evaluate(_make_action(raw_quantity=200.0))

        assert decision.approved is True
        assert decision.sized_quantity == pytest.approx(100.0)
        assert decision.rejection_reason is None

    def test_symbol_exposure_accumulates(self):
        engine = _make_engine(max_trade=500.0, max_symbol=1000.0)
        engine.evaluate(_make_action(symbol="AAPL", raw_quantity=300.0))
        engine.evaluate(_make_action(symbol="AAPL", raw_quantity=300.0))

        assert engine._symbol_exposure["AAPL"] == pytest.approx(600.0)

    def test_symbol_isolation(self):
        """Exposure tracked independently per symbol."""
        engine = _make_engine(max_trade=500.0, max_symbol=1000.0)
        # fill AAPL to limit
        engine.evaluate(_make_action(symbol="AAPL", raw_quantity=500.0))
        engine.evaluate(_make_action(symbol="AAPL", raw_quantity=500.0))
        # TSLA should still have full headroom
        decision = engine.evaluate(_make_action(symbol="TSLA", raw_quantity=400.0))

        assert decision.approved is True
        assert decision.sized_quantity == pytest.approx(400.0)


class TestRiskEngineRejections:
    def test_exceeds_trade_cap(self):
        engine = _make_engine(max_trade=500.0, max_symbol=1000.0)
        decision = engine.evaluate(_make_action(raw_quantity=501.0))

        assert decision.approved is False
        assert decision.sized_quantity is None
        assert decision.rejection_reason == "EXCEEDS_TRADE_CAP"

    def test_exceeds_symbol_exposure_no_headroom(self):
        engine = _make_engine(max_trade=500.0, max_symbol=1000.0)
        # fill the symbol bucket entirely across two trades
        engine.evaluate(_make_action(symbol="AAPL", raw_quantity=500.0))
        engine.evaluate(_make_action(symbol="AAPL", raw_quantity=500.0))
        # now headroom is exactly 0
        decision = engine.evaluate(_make_action(symbol="AAPL", raw_quantity=1.0))

        assert decision.approved is False
        assert decision.sized_quantity is None
        assert decision.rejection_reason == "EXCEEDS_SYMBOL_EXPOSURE"

    def test_rejected_trade_does_not_consume_exposure(self):
        """A rejected trade must not update _symbol_exposure."""
        engine = _make_engine(max_trade=500.0, max_symbol=1000.0)
        before = engine._symbol_exposure.get("AAPL", 0.0)

        # reject via trade cap
        engine.evaluate(_make_action(symbol="AAPL", raw_quantity=600.0))
        assert engine._symbol_exposure.get("AAPL", 0.0) == pytest.approx(before)

    def test_rejected_symbol_exposure_does_not_consume_budget(self):
        """A rejection due to zero headroom must not mutate state."""
        engine = _make_engine(max_trade=500.0, max_symbol=500.0)
        engine.evaluate(_make_action(symbol="AAPL", raw_quantity=500.0))
        before = engine._symbol_exposure["AAPL"]

        engine.evaluate(_make_action(symbol="AAPL", raw_quantity=1.0))
        assert engine._symbol_exposure["AAPL"] == pytest.approx(before)
