from unittest.mock import MagicMock

from handlers.grafana_alert_handler import GrafanaAlertHandler
from shared.notifications import NotificationMessage


class TestGrafanaAlertHandler:
    def _make_handler(self):
        channel = MagicMock()
        handler = GrafanaAlertHandler(channel)
        return handler, channel

    def _firing_payload(self, **overrides):
        alert = {
            "status": "firing",
            "labels": {
                "alertname": "Service Down: marketlistener",
                "job": "marketlistener",
                "service": "marketlistener",
                "severity": "critical",
            },
            "annotations": {
                "summary": "marketlistener is down — Prometheus scrape target unreachable",
            },
            "startsAt": "2026-08-15T12:00:00Z",
            "endsAt": "0001-01-01T00:00:00Z",
        }
        alert.update(overrides)
        return {"status": "firing", "alerts": [alert]}

    def _resolved_payload(self):
        return {
            "status": "resolved",
            "alerts": [
                {
                    "status": "resolved",
                    "labels": {
                        "alertname": "Service Down: marketlistener",
                        "job": "marketlistener",
                        "service": "marketlistener",
                        "severity": "critical",
                    },
                    "annotations": {
                        "summary": "marketlistener is down — Prometheus scrape target unreachable",
                    },
                    "startsAt": "2026-08-15T12:00:00Z",
                    "endsAt": "2026-08-15T12:05:00Z",
                },
            ],
        }

    def test_firing_alert_sends_red_notification(self):
        handler, channel = self._make_handler()
        handler.handle(self._firing_payload())

        channel.send.assert_called_once()
        msg = channel.send.call_args[0][0]
        assert isinstance(msg, NotificationMessage)
        assert "[ALERT]" in msg.title
        assert msg.color == "ff0000"

    def test_resolved_alert_sends_green_notification(self):
        handler, channel = self._make_handler()
        handler.handle(self._resolved_payload())

        channel.send.assert_called_once()
        msg = channel.send.call_args[0][0]
        assert "[RESOLVED]" in msg.title
        assert msg.color == "00ff00"
        assert "back online" in msg.body

    def test_fields_contain_service_and_status(self):
        handler, channel = self._make_handler()
        handler.handle(self._firing_payload())

        msg = channel.send.call_args[0][0]
        field_names = [f[0] for f in msg.fields]
        assert "Service" in field_names
        assert "Status" in field_names
        assert "Severity" in field_names
        assert "Instance" in field_names
        assert "Started" in field_names

    def test_service_field_uses_service_label(self):
        handler, channel = self._make_handler()
        handler.handle(self._firing_payload())

        msg = channel.send.call_args[0][0]
        service_field = next(f for f in msg.fields if f[0] == "Service")
        assert service_field[1] == "marketlistener"

    def test_falls_back_to_job_label_when_no_service(self):
        handler, channel = self._make_handler()
        payload = self._firing_payload()
        del payload["alerts"][0]["labels"]["service"]
        handler.handle(payload)

        msg = channel.send.call_args[0][0]
        service_field = next(f for f in msg.fields if f[0] == "Service")
        assert service_field[1] == "marketlistener"

    def test_multiple_alerts_in_single_payload(self):
        handler, channel = self._make_handler()
        payload = {
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "Down: A", "service": "a", "severity": "critical"},
                    "annotations": {"summary": "A is down"},
                    "startsAt": "2026-08-15T12:00:00Z",
                },
                {
                    "status": "firing",
                    "labels": {"alertname": "Down: B", "service": "b", "severity": "warning"},
                    "annotations": {"summary": "B is down"},
                    "startsAt": "2026-08-15T12:01:00Z",
                },
            ],
        }
        handler.handle(payload)
        assert channel.send.call_count == 2

    def test_warning_severity_uses_orange(self):
        handler, channel = self._make_handler()
        payload = self._firing_payload()
        payload["alerts"][0]["labels"]["severity"] = "warning"
        handler.handle(payload)

        msg = channel.send.call_args[0][0]
        assert msg.color == "ff8c00"

    def test_empty_alerts_list_does_nothing(self):
        handler, channel = self._make_handler()
        handler.handle({"status": "firing", "alerts": []})
        channel.send.assert_not_called()

    def test_send_failure_does_not_propagate(self):
        handler, channel = self._make_handler()
        channel.send.side_effect = RuntimeError("webhook down")
        handler.handle(self._firing_payload())
