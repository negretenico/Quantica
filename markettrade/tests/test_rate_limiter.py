from trade.rate_limiter import TradeRateLimiter


class TestTradeRateLimiter:

    def test_allows_under_limit(self):
        rl = TradeRateLimiter(max_per_minute=10)
        for i in range(9):
            allowed, reason = rl.check("BTCUSDT", now=1000.0 + i)
            assert allowed is True
            assert reason is None

    def test_blocks_at_limit(self):
        rl = TradeRateLimiter(max_per_minute=10)
        for i in range(10):
            allowed, _ = rl.check("BTCUSDT", now=1000.0 + i)
            assert allowed is True

        allowed, reason = rl.check("BTCUSDT", now=1009.5)
        assert allowed is False
        assert "rate_limited" in reason
        assert "10/10" in reason

    def test_window_expiry(self):
        rl = TradeRateLimiter(max_per_minute=10, window_seconds=60.0)
        for i in range(10):
            rl.check("BTCUSDT", now=1000.0 + i)

        allowed, reason = rl.check("BTCUSDT", now=1061.0)
        assert allowed is True
        assert reason is None

    def test_multi_symbol_independence(self):
        rl = TradeRateLimiter(max_per_minute=2)
        rl.check("BTCUSDT", now=1000.0)
        rl.check("BTCUSDT", now=1001.0)

        allowed, _ = rl.check("BTCUSDT", now=1002.0)
        assert allowed is False

        allowed, reason = rl.check("ETHUSDT", now=1002.0)
        assert allowed is True
        assert reason is None

    def test_partial_window_expiry(self):
        rl = TradeRateLimiter(max_per_minute=3, window_seconds=10.0)
        rl.check("BTCUSDT", now=100.0)
        rl.check("BTCUSDT", now=105.0)
        rl.check("BTCUSDT", now=109.0)

        allowed, _ = rl.check("BTCUSDT", now=109.5)
        assert allowed is False

        allowed, reason = rl.check("BTCUSDT", now=111.0)
        assert allowed is True
        assert reason is None

    def test_reason_string_format(self):
        rl = TradeRateLimiter(max_per_minute=1, window_seconds=30.0)
        rl.check("BTCUSDT", now=100.0)

        allowed, reason = rl.check("BTCUSDT", now=100.5)
        assert allowed is False
        assert reason == "rate_limited: 1/1 in 30s"

    def test_custom_max_and_window(self):
        rl = TradeRateLimiter(max_per_minute=3, window_seconds=10.0)
        for i in range(3):
            allowed, _ = rl.check("BTCUSDT", now=200.0 + i)
            assert allowed is True

        allowed, reason = rl.check("BTCUSDT", now=202.5)
        assert allowed is False
        assert "3/3" in reason
