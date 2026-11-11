import json
import os
import tempfile

from trade.portfolio import Portfolio, Position


class TestInitialState:
    def test_initial_cash(self):
        p = Portfolio(cash=100.0, starting_balance=100.0)
        assert p.cash == 100.0
        assert p.starting_balance == 100.0
        assert p.positions == {}
        assert p.realized_pnl == 0.0


class TestRecordBuy:
    def test_deducts_cash(self):
        p = Portfolio(cash=100.0, starting_balance=100.0)
        p.record_buy("BTCUSDT", entry_price=50000.0, sized_quantity=0.001)
        assert p.cash == pytest.approx(100.0 - 50000.0 * 0.001)

    def test_creates_position(self):
        p = Portfolio(cash=100.0, starting_balance=100.0)
        p.record_buy("BTCUSDT", entry_price=50000.0, sized_quantity=0.001)
        assert "BTCUSDT" in p.positions
        pos = p.positions["BTCUSDT"]
        assert pos.quantity == 0.001
        assert pos.avg_entry_price == 50000.0

    def test_averages_existing_position(self):
        p = Portfolio(cash=200.0, starting_balance=200.0)
        p.record_buy("BTCUSDT", entry_price=50000.0, sized_quantity=0.001)
        p.record_buy("BTCUSDT", entry_price=60000.0, sized_quantity=0.001)
        pos = p.positions["BTCUSDT"]
        assert pos.quantity == pytest.approx(0.002)
        expected_avg = (50000.0 * 0.001 + 60000.0 * 0.001) / 0.002
        assert pos.avg_entry_price == pytest.approx(expected_avg)


class TestRecordSell:
    def test_returns_cash_and_pnl(self):
        p = Portfolio(cash=100.0, starting_balance=100.0)
        p.record_buy("BTCUSDT", entry_price=50000.0, sized_quantity=0.001)
        cash_after_buy = p.cash
        p.record_sell("BTCUSDT", exit_price=55000.0, sized_quantity=0.001)
        assert p.cash == pytest.approx(cash_after_buy + 55000.0 * 0.001)
        assert p.realized_pnl == pytest.approx((55000.0 - 50000.0) * 0.001)
        assert "BTCUSDT" not in p.positions


class TestClosePosition:
    def test_close_position_full(self):
        p = Portfolio(cash=100.0, starting_balance=100.0)
        p.record_buy("ETHUSDT", entry_price=3000.0, sized_quantity=0.1)
        p.close_position("ETHUSDT", current_price=3500.0)
        assert "ETHUSDT" not in p.positions
        assert p.realized_pnl == pytest.approx((3500.0 - 3000.0) * 0.1)

    def test_close_position_idempotent(self):
        p = Portfolio(cash=100.0, starting_balance=100.0)
        p.close_position("NOPE", current_price=100.0)
        assert p.cash == 100.0
        assert p.realized_pnl == 0.0


class TestValuation:
    def test_total_value_with_price_fn(self):
        p = Portfolio(cash=50.0, starting_balance=100.0)
        p.record_buy("BTCUSDT", entry_price=50000.0, sized_quantity=0.001)
        value = p.total_value(lambda sym: 55000.0)
        assert value == pytest.approx(50.0 - 50000.0 * 0.001 + 55000.0 * 0.001)

    def test_unrealized_pnl(self):
        p = Portfolio(cash=100.0, starting_balance=100.0)
        p.record_buy("BTCUSDT", entry_price=50000.0, sized_quantity=0.001)
        pnl = p.unrealized_pnl(lambda sym: 55000.0)
        assert pnl == pytest.approx((55000.0 - 50000.0) * 0.001)


class TestPersistence:
    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "state.json")
            p = Portfolio(cash=100.0, starting_balance=100.0)
            p.record_buy("BTCUSDT", entry_price=50000.0, sized_quantity=0.001)
            p.realized_pnl = 2.5
            p.save(path)

            loaded = Portfolio.load(path, starting_balance=100.0)
            # cash = 100 - 50000*0.001 = 50.0
            assert loaded.cash == pytest.approx(50.0)
            assert loaded.starting_balance == 100.0
            assert loaded.realized_pnl == pytest.approx(2.5)
            assert "BTCUSDT" in loaded.positions
            assert loaded.positions["BTCUSDT"].quantity == pytest.approx(0.001)
            assert loaded.positions["BTCUSDT"].avg_entry_price == pytest.approx(50000.0)

    def test_load_missing_file(self):
        loaded = Portfolio.load("/nonexistent/path.json", starting_balance=100.0)
        assert loaded.cash == 100.0
        assert loaded.starting_balance == 100.0
        assert loaded.positions == {}

    def test_load_corrupt_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "state.json")
            with open(path, "w") as f:
                f.write("not json at all")
            loaded = Portfolio.load(path, starting_balance=100.0)
            assert loaded.cash == 100.0
            assert loaded.positions == {}


import pytest
