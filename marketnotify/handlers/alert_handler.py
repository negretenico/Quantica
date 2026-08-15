import logging
import time

from app.metrics import notification_latency
from shared.notifications import NotificationChannel, NotificationMessage

logger = logging.getLogger(__name__)

_COLORS = {
    ("alert", "floor"): "ff8c00",
    ("alert", "ceiling"): "ffcc00",
    ("alert_cleared", "floor"): "00ff00",
    ("alert_cleared", "ceiling"): "00ff00",
}


class AlertHandler:
    """Generic handler for ``type: alert`` and ``type: alert_cleared`` payloads.

    Formats a Discord embed from the payload fields and sends immediately.
    Has no knowledge of calibration, risk, or any specific domain — it renders
    whatever prefix/label/kind/value/threshold it receives.
    """

    def __init__(self, channel: NotificationChannel):
        self._channel = channel

    def handle(self, payload: dict) -> None:
        event_type = payload.get("type", "")
        if event_type not in ("alert", "alert_cleared"):
            return

        prefix = payload.get("prefix", "MONITOR")
        label = payload.get("label", "unknown")
        kind = payload.get("kind", "unknown")
        value = payload.get("value")
        threshold = payload.get("threshold")
        source = payload.get("source", "unknown")
        timestamp = payload.get("timestamp_utc", "N/A")

        if event_type == "alert":
            title = f"[{prefix}] {kind} breach — {label}"
            body = f"{kind.capitalize()} threshold breached on {source}."
        else:
            title = f"[{prefix}] {kind} cleared — {label}"
            body = f"{kind.capitalize()} condition cleared on {source}."

        fields = [
            ("Label", label),
            ("Kind", kind),
            ("Value", f"{value:.4f}" if value is not None else "N/A"),
            ("Threshold", f"{threshold}" if threshold is not None else "N/A"),
            ("Source", source),
            ("Timestamp", timestamp),
        ]

        color = _COLORS.get((event_type, kind), "808080")

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
            logger.info("Alert notification sent: %s", title)
        except Exception:
            logger.exception("Failed to send alert notification: %s", title)
