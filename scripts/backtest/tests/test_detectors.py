"""Tests for scripts/backtest/detectors.py

All streams are hand-crafted in memory — no disk I/O.
"""

from scripts.backtest.detectors import dominant_side, large_trade, price_spike

_SIGNAL_KEYS = {"symbol", "eventTime", "type", "reason", "price", "quantity", "side", "metadata"}


def _trade(
    symbol: str = "BTCUSDT",
    price: str = "100.00",
    quantity: str = "1.0",
    side: str = "BUY",
    event_time: int = 1_000,
) -> dict:
    return {
        "symbol": symbol,
        "price": price,
        "quantity": quantity,
        "side": side,
        "eventTime": event_time,
    }


# ---------------------------------------------------------------------------
# large_trade
# ---------------------------------------------------------------------------


class TestLargeTrade:
    def test_fires_above_threshold(self):
        trades = [_trade(quantity="1000001.0")]
        signals = large_trade(trades)
        assert len(signals) == 1
        assert signals[0]["type"] == "LARGE_TRADE"

    def test_does_not_fire_at_threshold(self):
        trades = [_trade(quantity="1000000.0")]
        signals = large_trade(trades)
        assert signals == []

    def test_does_not_fire_below_threshold(self):
        trades = [_trade(quantity="999999.99")]
        signals = large_trade(trades)
        assert signals == []

    def test_multiple_fires_in_stream(self):
        trades = [
            _trade(quantity="1000001.0", event_time=1),
            _trade(quantity="500.0", event_time=2),
            _trade(quantity="2000000.0", event_time=3),
        ]
        signals = large_trade(trades)
        assert len(signals) == 2
        assert signals[0]["eventTime"] == 1
        assert signals[1]["eventTime"] == 3

    def test_signal_shape(self):
        trades = [_trade(quantity="1500000.0", price="66000.00", side="SELL", event_time=42)]
        signals = large_trade(trades)
        s = signals[0]
        assert _SIGNAL_KEYS.issubset(s.keys())
        assert s["symbol"] == "BTCUSDT"
        assert s["price"] == 66000.00
        assert s["quantity"] == 1_500_000.0
        assert s["side"] == "SELL"
        assert s["eventTime"] == 42
        assert s["metadata"]["threshold"] == 1_000_000

    def test_custom_threshold(self):
        trades = [_trade(quantity="600.0")]
        assert large_trade(trades, threshold=500) == [
            {
                "symbol": "BTCUSDT",
                "eventTime": 1_000,
                "type": "LARGE_TRADE",
                "reason": "Quantity 600.0 exceeded threshold 500",
                "price": 100.0,
                "quantity": 600.0,
                "side": "BUY",
                "metadata": {"threshold": 500},
            }
        ]

    def test_empty_stream(self):
        assert large_trade([]) == []

    def test_per_symbol_independent(self):
        trades = [
            _trade(symbol="BTCUSDT", quantity="1000001.0"),
            _trade(symbol="ETHUSDT", quantity="0.5"),
        ]
        signals = large_trade(trades)
        assert len(signals) == 1
        assert signals[0]["symbol"] == "BTCUSDT"


# ---------------------------------------------------------------------------
# price_spike
# ---------------------------------------------------------------------------


class TestPriceSpike:
    def test_first_trade_does_not_fire(self):
        trades = [_trade(price="100.0")]
        assert price_spike(trades) == []

    def test_fires_above_pct_threshold(self):
        # seed with price 100, then send 103 (3% deviation > 2% default)
        trades = [
            _trade(price="100.0", event_time=1),
            _trade(price="103.0", event_time=2),
        ]
        signals = price_spike(trades)
        assert len(signals) == 1
        assert signals[0]["type"] == "PRICE_SPIKE"
        assert signals[0]["eventTime"] == 2

    def test_does_not_fire_at_threshold(self):
        # exactly 2% from 100 should NOT fire (strictly greater than)
        trades = [
            _trade(price="100.0", event_time=1),
            _trade(price="102.0", event_time=2),
        ]
        signals = price_spike(trades)
        assert signals == []

    def test_does_not_fire_below_threshold(self):
        trades = [
            _trade(price="100.0", event_time=1),
            _trade(price="101.0", event_time=2),
        ]
        assert price_spike(trades) == []

    def test_signal_shape(self):
        trades = [
            _trade(price="100.0", event_time=1),
            _trade(price="105.0", event_time=2, quantity="0.5", side="SELL"),
        ]
        s = price_spike(trades)[0]
        assert _SIGNAL_KEYS.issubset(s.keys())
        assert s["type"] == "PRICE_SPIKE"
        assert s["symbol"] == "BTCUSDT"
        assert s["price"] == 105.0
        assert s["quantity"] == 0.5
        assert s["side"] == "SELL"
        assert "priceChange" in s["metadata"]
        assert "movingAverage" in s["metadata"]
        assert "threshold" in s["metadata"]

    def test_multiple_fires_in_stream(self):
        # 100 seeds, 105 fires, 105 added -> avg ~102.5, 200 fires
        trades = [
            _trade(price="100.0", event_time=1),
            _trade(price="105.0", event_time=2),
            _trade(price="200.0", event_time=3),
        ]
        signals = price_spike(trades)
        assert len(signals) == 2

    def test_per_symbol_isolation(self):
        # BTC seeds, ETH seeds; only ETH spikes
        trades = [
            _trade(symbol="BTCUSDT", price="100.0", event_time=1),
            _trade(symbol="ETHUSDT", price="100.0", event_time=2),
            _trade(symbol="BTCUSDT", price="101.0", event_time=3),  # 1% — no fire
            _trade(symbol="ETHUSDT", price="110.0", event_time=4),  # 10% — fire
        ]
        signals = price_spike(trades)
        assert len(signals) == 1
        assert signals[0]["symbol"] == "ETHUSDT"
        assert signals[0]["eventTime"] == 4

    def test_rolling_window_caps_at_window_size(self):
        # Fill window of size 3 with 100s, then send a spike; avg must stay near 100
        trades = [_trade(price="100.0", event_time=i) for i in range(10)]
        trades.append(_trade(price="200.0", event_time=99))
        signals = price_spike(trades, window=3)
        assert len(signals) == 1

    def test_state_resets_between_calls(self):
        # Two separate calls must start fresh; second call should not inherit prior window
        trades1 = [_trade(price="100.0", event_time=1)]
        price_spike(trades1)  # seeds window internally but that state is discarded
        trades2 = [_trade(price="100.0", event_time=2)]
        # First trade in a fresh call never fires
        assert price_spike(trades2) == []

    def test_empty_stream(self):
        assert price_spike([]) == []

    def test_custom_pct(self):
        trades = [
            _trade(price="100.0", event_time=1),
            _trade(price="100.5", event_time=2),  # 0.5% > 0.4% custom threshold
        ]
        signals = price_spike(trades, pct=0.004)
        assert len(signals) == 1


# ---------------------------------------------------------------------------
# dominant_side
# ---------------------------------------------------------------------------


class TestDominantSide:
    def test_fires_at_streak_threshold(self):
        trades = [_trade(side="BUY", event_time=i) for i in range(5)]
        signals = dominant_side(trades)
        assert len(signals) == 1
        assert signals[0]["type"] == "DOMINANT_SIDE"
        assert signals[0]["eventTime"] == 4

    def test_does_not_fire_below_streak(self):
        trades = [_trade(side="BUY", event_time=i) for i in range(4)]
        assert dominant_side(trades) == []

    def test_streak_resets_to_zero_after_fire(self):
        # 5 BUYs fire, then 4 more BUYs should not fire again (streak reset to 0, then 1,2,3,4)
        trades = [_trade(side="BUY", event_time=i) for i in range(9)]
        signals = dominant_side(trades)
        assert len(signals) == 1

    def test_fires_again_after_reset(self):
        # 5 BUYs fire (streak→0), then 5 more BUYs fire again
        trades = [_trade(side="BUY", event_time=i) for i in range(10)]
        signals = dominant_side(trades)
        assert len(signals) == 2

    def test_side_flip_resets_streak(self):
        trades = [
            _trade(side="BUY", event_time=1),
            _trade(side="BUY", event_time=2),
            _trade(side="BUY", event_time=3),
            _trade(side="BUY", event_time=4),
            _trade(side="SELL", event_time=5),  # flip — streak resets to 1
            _trade(side="BUY", event_time=6),   # BUY again — streak back to 1
        ]
        signals = dominant_side(trades)
        assert signals == []

    def test_side_flip_then_new_streak_fires(self):
        # 4 BUYs, 1 SELL (flip, reset), then 5 SELLs fire
        trades = (
            [_trade(side="BUY", event_time=i) for i in range(4)]
            + [_trade(side="SELL", event_time=i + 10) for i in range(5)]
        )
        signals = dominant_side(trades)
        assert len(signals) == 1
        assert signals[0]["side"] == "SELL"

    def test_signal_shape(self):
        trades = [_trade(side="BUY", event_time=i) for i in range(5)]
        s = dominant_side(trades)[0]
        assert _SIGNAL_KEYS.issubset(s.keys())
        assert s["type"] == "DOMINANT_SIDE"
        assert s["metadata"]["streakCount"] == 5
        assert "BUY" in s["reason"]

    def test_per_symbol_isolation(self):
        # BTC has 4 BUYs, ETH has 5 BUYs — only ETH fires
        btc = [_trade(symbol="BTCUSDT", side="BUY", event_time=i) for i in range(4)]
        eth = [_trade(symbol="ETHUSDT", side="BUY", event_time=i + 10) for i in range(5)]
        signals = dominant_side(btc + eth)
        assert len(signals) == 1
        assert signals[0]["symbol"] == "ETHUSDT"

    def test_multiple_symbols_interleaved(self):
        # Interleaved BTC and ETH BUYs — each tracked independently
        trades = []
        for i in range(5):
            trades.append(_trade(symbol="BTCUSDT", side="BUY", event_time=i * 2))
            trades.append(_trade(symbol="ETHUSDT", side="BUY", event_time=i * 2 + 1))
        signals = dominant_side(trades)
        assert len(signals) == 2
        symbols = {s["symbol"] for s in signals}
        assert symbols == {"BTCUSDT", "ETHUSDT"}

    def test_custom_streak(self):
        trades = [_trade(side="BUY", event_time=i) for i in range(3)]
        signals = dominant_side(trades, streak=3)
        assert len(signals) == 1

    def test_empty_stream(self):
        assert dominant_side([]) == []

    def test_first_trade_does_not_fire(self):
        assert dominant_side([_trade(side="BUY")]) == []
