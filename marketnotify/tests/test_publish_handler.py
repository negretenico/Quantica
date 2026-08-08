from unittest.mock import MagicMock, call

from app.metrics import notification_latency
from handlers.publish_handler import PublishHandler
from shared.notifications import NotificationMessage


class TestPublishHandler:
    def _make_handler(self):
        channel = MagicMock()
        handler = PublishHandler(channel)
        return handler, channel

    def test_failure_dispatches_immediately(self):
        handler, channel = self._make_handler()
        payload = {
            "type": "publish_failure",
            "source": "markettrade",
            "error": "disk full",
            "timestamp_utc": "2026-08-01T12:00:00",
        }
        handler.handle(payload)

        channel.send.assert_called_once()
        msg = channel.send.call_args[0][0]
        assert isinstance(msg, NotificationMessage)
        assert "FAILURE" in msg.title
        assert "markettrade" in msg.title
        assert "disk full" in msg.body
        assert msg.color == "ff0000"

    def test_success_is_batched_not_immediate(self):
        handler, channel = self._make_handler()
        payload = {
            "type": "publish_success",
            "source": "markettrade",
            "symbol": "BTCUSDT",
            "action": "BUY",
            "timestamp_utc": "2026-08-01T12:00:00",
        }
        handler.handle(payload)

        # Success events are batched, not sent immediately
        channel.send.assert_not_called()

    def test_flush_successes_sends_batch(self):
        handler, channel = self._make_handler()

        for i in range(3):
            handler.handle({
                "type": "publish_success",
                "source": "markettrade",
                "symbol": f"SYM{i}",
                "action": "BUY",
                "timestamp_utc": "2026-08-01T12:00:00",
            })
        handler.handle({
            "type": "publish_success",
            "source": "marketbard",
            "symbol": "BTCUSDT",
            "action": "WRITE",
            "timestamp_utc": "2026-08-01T12:00:00",
        })

        # Manually trigger flush
        handler._flush_successes()

        channel.send.assert_called_once()
        msg = channel.send.call_args[0][0]
        assert isinstance(msg, NotificationMessage)
        assert "4 events" in msg.title
        assert msg.color == "00ff00"
        # Should have fields for each source
        field_names = [f[0] for f in msg.fields]
        assert "markettrade" in field_names
        assert "marketbard" in field_names

    def test_flush_with_empty_batch_does_nothing(self):
        handler, channel = self._make_handler()
        handler._flush_successes()
        channel.send.assert_not_called()

    def test_unknown_type_is_ignored(self):
        handler, channel = self._make_handler()
        handler.handle({"type": "unknown_event"})
        channel.send.assert_not_called()

    def test_failure_records_latency(self):
        handler, channel = self._make_handler()
        before = notification_latency._sum.get()
        handler.handle({
            "type": "publish_failure",
            "source": "markettrade",
            "error": "timeout",
            "timestamp_utc": "2026-08-01T12:00:00",
        })
        assert notification_latency._sum.get() > before

    def test_flush_records_latency(self):
        handler, channel = self._make_handler()
        handler.handle({
            "type": "publish_success",
            "source": "markettrade",
            "symbol": "BTCUSDT",
            "action": "BUY",
            "timestamp_utc": "2026-08-01T12:00:00",
        })
        before = notification_latency._sum.get()
        handler._flush_successes()
        assert notification_latency._sum.get() > before
