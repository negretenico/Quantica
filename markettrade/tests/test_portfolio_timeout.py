import time

import pytest

from trade.portfolio import Portfolio, PositionTimeoutScheduler


class TestTimeoutClosesPosition:
    def test_timeout_closes_position(self):
        p = Portfolio(cash=100.0, starting_balance=100.0)
        p.record_buy("BTCUSDT", entry_price=50000.0, sized_quantity=0.001)

        closed = []

        def on_close(symbol, realized):
            closed.append(symbol)

        scheduler = PositionTimeoutScheduler(
            portfolio=p,
            timeout_seconds=0.2,
            price_source=lambda sym: 55000.0,
            on_close=on_close,
        )
        scheduler.schedule("BTCUSDT")
        time.sleep(1.0)
        scheduler.stop()

        assert "BTCUSDT" not in p.positions
        assert "BTCUSDT" in closed
        assert p.realized_pnl == pytest.approx((55000.0 - 50000.0) * 0.001)


class TestCancelPreventsClose:
    def test_cancel_prevents_close(self):
        p = Portfolio(cash=100.0, starting_balance=100.0)
        p.record_buy("BTCUSDT", entry_price=50000.0, sized_quantity=0.001)

        closed = []

        scheduler = PositionTimeoutScheduler(
            portfolio=p,
            timeout_seconds=0.3,
            price_source=lambda sym: 55000.0,
            on_close=lambda sym, r: closed.append(sym),
        )
        scheduler.schedule("BTCUSDT")
        scheduler.cancel("BTCUSDT")
        time.sleep(1.0)
        scheduler.stop()

        assert "BTCUSDT" in p.positions
        assert closed == []


class TestPriceFallback:
    def test_price_fallback_on_failure(self):
        p = Portfolio(cash=100.0, starting_balance=100.0)
        p.record_buy("BTCUSDT", entry_price=50000.0, sized_quantity=0.001)

        closed = []

        scheduler = PositionTimeoutScheduler(
            portfolio=p,
            timeout_seconds=0.2,
            price_source=lambda sym: None,  # price fetch fails
            on_close=lambda sym, r: closed.append(sym),
        )
        scheduler.schedule("BTCUSDT")
        time.sleep(1.0)
        scheduler.stop()

        assert "BTCUSDT" not in p.positions
        assert "BTCUSDT" in closed
        # Falls back to entry price, so realized PnL is 0
        assert p.realized_pnl == pytest.approx(0.0)
