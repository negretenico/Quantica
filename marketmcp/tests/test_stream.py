"""Unit tests for app.stream — TokenBucket, SignalStream cache and dedup."""

import time
from unittest.mock import patch, MagicMock

from app.config import Config
from app.stream import TokenBucket, SignalStream


class TestTokenBucket:
    def test_allows_within_capacity(self):
        bucket = TokenBucket(rate=10.0, capacity=10.0)
        # Should allow up to 10 tokens immediately
        for _ in range(10):
            assert bucket.consume() is True

    def test_rejects_when_empty(self):
        bucket = TokenBucket(rate=1.0, capacity=1.0)
        assert bucket.consume() is True
        assert bucket.consume() is False

    def test_refills_over_time(self):
        bucket = TokenBucket(rate=100.0, capacity=1.0)
        assert bucket.consume() is True
        assert bucket.consume() is False
        # Wait enough for a refill
        time.sleep(0.02)
        assert bucket.consume() is True

    def test_capacity_limits_burst(self):
        bucket = TokenBucket(rate=100.0, capacity=3.0)
        # Start with full capacity
        assert bucket.consume() is True
        assert bucket.consume() is True
        assert bucket.consume() is True
        assert bucket.consume() is False


class TestSignalStream:
    def _make_config(self, **overrides):
        """Create a Config with streaming defaults, patching env."""
        defaults = {
            "STREAM_ENABLED": True,
            "STREAM_MAX_EVENTS_PER_SEC": 100,
            "STREAM_CACHE_SIZE_PER_SYMBOL": 5,
            "DEDUP_MAXLEN": 100,
            "RABBITMQ_URL": "amqp://guest:guest@localhost:5672/",
            "SIGNAL_QUEUE": "signal.mcp",
            "SIGNAL_EXCHANGE": "signal",
            "ANALYTICS_QUEUE": "analytics.mcp",
            "ANALYTICS_EXCHANGE": "analytics",
            "ANALYTICS_ROUTING_KEY": "signal.analytics.#",
        }
        defaults.update(overrides)
        config = Config()
        for k, v in defaults.items():
            setattr(config, k, v)
        return config

    @patch("app.stream.RabbitConsumer")
    def test_handler_deduplicates_events(self, mock_consumer_cls):
        config = self._make_config()
        stream = SignalStream(config)

        event = {"symbol": "BTCUSDT", "eventTime": "123456", "type": "AGGRESSIVE_BUY"}

        # First call should store
        stream._process_event(event, source="signal")
        assert stream.has_data() is True
        assert len(stream.get_latest("BTCUSDT")) == 1

        # Second call (duplicate) should be dropped
        stream._process_event(event, source="signal")
        assert len(stream.get_latest("BTCUSDT")) == 1

    @patch("app.stream.RabbitConsumer")
    def test_handler_rate_limits_events(self, mock_consumer_cls):
        config = self._make_config(STREAM_MAX_EVENTS_PER_SEC=2)
        stream = SignalStream(config)

        # Send 5 unique events rapidly — only first 2 should pass rate limiter
        for i in range(5):
            event = {"symbol": "ETHUSDT", "eventTime": str(i), "type": "AGGRESSIVE_SELL"}
            stream._process_event(event, source="signal")

        # Rate limiter starts with capacity=rate=2, so 2 pass
        assert len(stream.get_latest("ETHUSDT")) == 2

    @patch("app.stream.RabbitConsumer")
    def test_cache_stores_last_n_per_symbol(self, mock_consumer_cls):
        config = self._make_config(
            STREAM_MAX_EVENTS_PER_SEC=1000,
            STREAM_CACHE_SIZE_PER_SYMBOL=3,
        )
        stream = SignalStream(config)

        # Insert 5 events — cache should keep only last 3
        for i in range(5):
            event = {"symbol": "BTCUSDT", "eventTime": str(i), "type": "AGGRESSIVE_BUY"}
            stream._process_event(event, source="signal")

        events = stream.get_latest("BTCUSDT")
        assert len(events) == 3
        # Should be the last 3 (eventTime 2, 3, 4)
        assert events[0]["eventTime"] == "2"
        assert events[2]["eventTime"] == "4"

    @patch("app.stream.RabbitConsumer")
    def test_get_latest_filters_by_symbol(self, mock_consumer_cls):
        config = self._make_config(STREAM_MAX_EVENTS_PER_SEC=1000)
        stream = SignalStream(config)

        stream._process_event({"symbol": "BTCUSDT", "eventTime": "1", "type": "BUY"}, source="signal")
        stream._process_event({"symbol": "ETHUSDT", "eventTime": "2", "type": "SELL"}, source="signal")

        btc_events = stream.get_latest("BTCUSDT")
        eth_events = stream.get_latest("ETHUSDT")
        missing = stream.get_latest("XRPUSDT")

        assert len(btc_events) == 1
        assert btc_events[0]["symbol"] == "BTCUSDT"
        assert len(eth_events) == 1
        assert eth_events[0]["symbol"] == "ETHUSDT"
        assert missing == []

    @patch("app.stream.RabbitConsumer")
    def test_get_all_latest_returns_all(self, mock_consumer_cls):
        config = self._make_config(STREAM_MAX_EVENTS_PER_SEC=1000)
        stream = SignalStream(config)

        stream._process_event({"symbol": "BTCUSDT", "eventTime": "1", "type": "BUY"}, source="signal")
        stream._process_event({"symbol": "ETHUSDT", "eventTime": "2", "type": "SELL"}, source="analytics")

        all_events = stream.get_all_latest()
        assert len(all_events) == 2
        symbols = {e["symbol"] for e in all_events}
        assert symbols == {"BTCUSDT", "ETHUSDT"}

    @patch("app.stream.RabbitConsumer")
    def test_has_data_false_when_empty(self, mock_consumer_cls):
        config = self._make_config()
        stream = SignalStream(config)
        assert stream.has_data() is False

    @patch("app.stream.RabbitConsumer")
    def test_handler_callback_signature(self, mock_consumer_cls):
        """Verify the handler works with (payload, queue) signature from RabbitConsumer."""
        config = self._make_config(STREAM_MAX_EVENTS_PER_SEC=1000)
        stream = SignalStream(config)

        event = {"symbol": "BTCUSDT", "eventTime": "100", "type": "AGGRESSIVE_BUY"}
        # Simulate RabbitConsumer calling the handler with (payload, queue)
        stream._handle_signal(event, "signal.mcp")
        assert len(stream.get_latest("BTCUSDT")) == 1

        event2 = {"symbol": "ETHUSDT", "eventTime": "200", "type": "CLUSTER"}
        stream._handle_analytics(event2, "analytics.mcp")
        assert len(stream.get_latest("ETHUSDT")) == 1
