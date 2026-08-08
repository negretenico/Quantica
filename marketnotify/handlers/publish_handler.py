import logging
import threading
import time

from app.metrics import notification_latency
from shared.notifications import NotificationChannel, NotificationMessage

logger = logging.getLogger(__name__)

_BATCH_INTERVAL_SECONDS = 60


class PublishHandler:
    """Batches publish success events and dispatches immediately on failures."""

    def __init__(self, channel: NotificationChannel):
        self._channel = channel
        self._lock = threading.Lock()
        self._success_batch: list[dict] = []
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._flush_loop, name="publish_handler_flush", daemon=True)
        self._thread.start()
        logger.info("Publish handler flush thread started (interval=%ds)", _BATCH_INTERVAL_SECONDS)

    def handle(self, payload: dict):
        event_type = payload.get("type", "")

        if event_type == "publish_failure":
            self._send_failure(payload)
            return

        if event_type == "publish_success":
            with self._lock:
                self._success_batch.append(payload)

    def _flush_loop(self):
        while True:
            time.sleep(_BATCH_INTERVAL_SECONDS)
            try:
                self._flush_successes()
            except Exception:
                logger.exception("Error flushing success batch")

    def _flush_successes(self):
        with self._lock:
            batch = self._success_batch
            self._success_batch = []

        if not batch:
            return

        sources = {}
        for event in batch:
            src = event.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1

        fields = [(source, f"{count} events") for source, count in sources.items()]

        message = NotificationMessage(
            title=f"Publish Summary ({len(batch)} events)",
            body="Successful publishes in the last 60 seconds.",
            fields=fields,
            color="00ff00",
        )

        try:
            start = time.time()
            self._channel.send(message)
            notification_latency.observe(time.time() - start)
            logger.debug("Flushed %d success events to Discord", len(batch))
        except Exception:
            logger.exception("Failed to send success batch notification")

    def _send_failure(self, payload: dict):
        source = payload.get("source", "unknown")
        error = payload.get("error", "unknown error")

        message = NotificationMessage(
            title=f"Publish FAILURE ({source})",
            body=f"Error: {error}",
            fields=[
                ("Source", source),
                ("Timestamp", payload.get("timestamp_utc", "N/A")),
            ],
            color="ff0000",
        )

        try:
            start = time.time()
            self._channel.send(message)
            notification_latency.observe(time.time() - start)
        except Exception:
            logger.exception("Failed to send failure notification")
