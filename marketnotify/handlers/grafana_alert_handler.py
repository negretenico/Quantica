import logging
import time

from app.metrics import grafana_alerts_received_total, notification_latency
from shared.notifications import NotificationChannel, NotificationMessage

logger = logging.getLogger(__name__)

_SEVERITY_COLORS = {
    "critical": "ff0000",
    "warning": "ff8c00",
    "info": "3498db",
}


class GrafanaAlertHandler:
    """Receives Grafana unified-alerting webhook payloads and sends
    formatted Discord notifications through the shared channel.

    Grafana webhook payload shape (POST JSON)::

        {
          "status": "firing" | "resolved",
          "alerts": [
            {
              "status": "firing" | "resolved",
              "labels": {"alertname": "...", "job": "...", "severity": "..."},
              "annotations": {"summary": "..."},
              "startsAt": "...",
              "endsAt": "...",
              ...
            }
          ],
          ...
        }
    """

    def __init__(self, channel: NotificationChannel):
        self._channel = channel

    def handle(self, payload: dict) -> None:
        alerts = payload.get("alerts", [])
        for alert in alerts:
            grafana_alerts_received_total.labels(status=alert.get("status", "unknown")).inc()
            status = alert.get("status", "unknown")
            labels = alert.get("labels", {})
            annotations = alert.get("annotations", {})

            service = labels.get("service", labels.get("job", "unknown"))
            alertname = labels.get("alertname", "Service Alert")
            severity = labels.get("severity", "critical")
            summary = annotations.get("summary", "No details available")
            instance = labels.get("instance", "N/A")
            started = alert.get("startsAt", "N/A")

            if status == "resolved":
                title = f"[RESOLVED] {alertname}"
                body = f"{service} is back online."
                color = "00ff00"
            else:
                title = f"[ALERT] {alertname}"
                body = summary
                color = _SEVERITY_COLORS.get(severity, "ff0000")

            fields = [
                ("Service", service),
                ("Status", status.upper()),
                ("Severity", severity),
                ("Instance", instance),
                ("Started", started),
            ]

            message = NotificationMessage(
                title=title,
                body=body,
                fields=fields,
                color=color,
            )

            try:
                start = time.time()
                self._channel.send(message)
                notification_latency.observe(time.time() - start)
                logger.info("Grafana alert notification sent: %s — %s", title, service)
            except Exception:
                logger.exception("Failed to send Grafana alert: %s", title)
