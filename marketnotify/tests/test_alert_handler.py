from unittest.mock import MagicMock

from handlers.alert_handler import AlertHandler
from shared.notifications import NotificationMessage


class TestAlertHandler:
    def _make_handler(self):
        channel = MagicMock()
        handler = AlertHandler(channel)
        return handler, channel

    def test_alert_sends_immediately(self):
        handler, channel = self._make_handler()
        payload = {
            "type": "alert",
            "prefix": "CALIBRATION",
            "label": "[0.7, 0.8)",
            "kind": "floor",
            "value": 0.35,
            "threshold": 0.40,
            "source": "markettrade",
            "timestamp_utc": "2026-08-01T12:00:00",
        }
        handler.handle(payload)

        channel.send.assert_called_once()
        msg = channel.send.call_args[0][0]
        assert isinstance(msg, NotificationMessage)
        assert "[CALIBRATION]" in msg.title
        assert "floor" in msg.title
        assert "[0.7, 0.8)" in msg.title

    def test_alert_cleared_sends_immediately(self):
        handler, channel = self._make_handler()
        payload = {
            "type": "alert_cleared",
            "prefix": "CALIBRATION",
            "label": "[0.7, 0.8)",
            "kind": "floor",
            "value": 0.55,
            "threshold": 0.40,
            "source": "markettrade",
            "timestamp_utc": "2026-08-01T12:00:00",
        }
        handler.handle(payload)

        channel.send.assert_called_once()
        msg = channel.send.call_args[0][0]
        assert "cleared" in msg.title
        assert msg.color == "00ff00"

    def test_floor_alert_color_is_orange(self):
        handler, channel = self._make_handler()
        handler.handle({
            "type": "alert",
            "prefix": "TEST",
            "label": "a",
            "kind": "floor",
            "value": 0.1,
            "threshold": 0.5,
            "source": "test",
        })
        msg = channel.send.call_args[0][0]
        assert msg.color == "ff8c00"

    def test_ceiling_alert_color_is_yellow(self):
        handler, channel = self._make_handler()
        handler.handle({
            "type": "alert",
            "prefix": "TEST",
            "label": "a",
            "kind": "ceiling",
            "value": 0.95,
            "threshold": 0.85,
            "source": "test",
        })
        msg = channel.send.call_args[0][0]
        assert msg.color == "ffcc00"

    def test_ignores_unknown_type(self):
        handler, channel = self._make_handler()
        handler.handle({"type": "publish_success", "source": "x"})
        channel.send.assert_not_called()

    def test_fields_contain_all_payload_info(self):
        handler, channel = self._make_handler()
        handler.handle({
            "type": "alert",
            "prefix": "RISK",
            "label": "BTCUSDT",
            "kind": "ceiling",
            "value": 0.92,
            "threshold": 0.85,
            "source": "markettrade",
            "timestamp_utc": "2026-08-13T10:00:00",
        })
        msg = channel.send.call_args[0][0]
        field_names = [f[0] for f in msg.fields]
        assert "Label" in field_names
        assert "Kind" in field_names
        assert "Value" in field_names
        assert "Threshold" in field_names
        assert "Source" in field_names
        assert "Timestamp" in field_names

    def test_generic_prefix_in_title(self):
        handler, channel = self._make_handler()
        handler.handle({
            "type": "alert",
            "prefix": "RISK",
            "label": "exposure",
            "kind": "ceiling",
            "value": 0.95,
            "threshold": 0.80,
            "source": "markettrade",
        })
        msg = channel.send.call_args[0][0]
        assert "[RISK]" in msg.title

    def test_send_failure_does_not_propagate(self):
        handler, channel = self._make_handler()
        channel.send.side_effect = RuntimeError("webhook down")
        # should not raise
        handler.handle({
            "type": "alert",
            "prefix": "TEST",
            "label": "a",
            "kind": "floor",
            "value": 0.1,
            "threshold": 0.5,
            "source": "test",
        })
