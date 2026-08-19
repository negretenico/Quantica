import datetime
import logging
import threading
import time

from app.config import Config
from app.metrics import alerts_published_total, alerts_throttled_total
from rabbitmq.publisher import RabbitPublisher

logger = logging.getLogger(__name__)

_ROUTING_KEY = "alert.marketanalysis"


class PipelineAlerter:
    """Publishes ML pipeline alerts to the notifications exchange with time-window throttling."""

    def __init__(
        self,
        publisher: RabbitPublisher,
        throttle_window: int = Config.ALERT_THROTTLE_WINDOW_SECONDS,
    ):
        self._publisher = publisher
        self._throttle_window = throttle_window
        self._last_alerted: dict[tuple[str, str], float] = {}
        self._lock = threading.Lock()

    def send_alert(self, symbol: str, failure_type: str, detail: str):
        with self._lock:
            now = time.monotonic()
            key = (symbol, failure_type)

            # Prune stale entries (older than 2x window)
            cutoff = now - self._throttle_window * 2
            self._last_alerted = {
                k: v for k, v in self._last_alerted.items() if v > cutoff
            }

            if key in self._last_alerted and now - self._last_alerted[key] < self._throttle_window:
                alerts_throttled_total.labels(alert_type=failure_type).inc()
                return

            payload = {
                "type": "alert",
                "prefix": "ML_PIPELINE",
                "label": symbol,
                "kind": failure_type,
                "value": None,
                "threshold": None,
                "source": "marketanalysis",
                "detail": detail,
                "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }

            try:
                self._publisher.publish(routing_key=_ROUTING_KEY, payload=payload)
                alerts_published_total.labels(alert_type=failure_type).inc()
                self._last_alerted[key] = now
                logger.warning("Alert published: %s %s — %s", failure_type, symbol, detail)
            except Exception:
                logger.exception("Failed to publish alert for %s/%s", symbol, failure_type)
