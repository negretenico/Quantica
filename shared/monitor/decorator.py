import logging
import threading
from datetime import datetime, timezone
from functools import wraps

logger = logging.getLogger(__name__)


def metric_monitor(
    publisher=None,
    routing_key: str = "alert",
    prefix: str = "MONITOR",
    thresholds: dict | None = None,
    source: str = "unknown",
):
    """Decorator that adds drift/overfit monitoring to any function returning metrics.

    The wrapped function must return ``dict[str, tuple[float, int]]`` mapping
    label → (value, sample_count).  After each call the decorator checks every
    label against configurable floor/ceiling thresholds and publishes a generic
    alert payload to the given ``publisher`` (a ``RabbitPublisher``).

    Alerts fire once per (label, kind) and are suppressed until the condition
    clears, then re-arm.

    Parameters
    ----------
    publisher : RabbitPublisher | None
        Where to send alert payloads.  ``None`` disables publishing but the
        wrapped function still executes normally.
    routing_key : str
        RabbitMQ routing key for alert messages.
    prefix : str
        Tag prepended to alert titles (e.g. ``"CALIBRATION"``).
    thresholds : dict
        ``{"floor": float, "ceiling": float, "min_samples": int}``.
    source : str
        Originating service name included in the alert payload.
    """

    if thresholds is None:
        thresholds = {}

    floor = thresholds.get("floor")
    ceiling = thresholds.get("ceiling")
    min_samples = thresholds.get("min_samples", 0)

    def decorator(fn):
        active_alerts: dict[tuple[str, str], bool] = {}
        lock = threading.Lock()

        @wraps(fn)
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)

            if not isinstance(result, dict):
                return result

            for label, entry in result.items():
                value, count = entry

                if count < min_samples:
                    continue

                _check_threshold(label, "floor", value, floor, lambda v, t: v < t, active_alerts, lock, publisher, routing_key, prefix, source)
                _check_threshold(label, "ceiling", value, ceiling, lambda v, t: v > t, active_alerts, lock, publisher, routing_key, prefix, source)

            return result

        wrapper._active_alerts = active_alerts
        wrapper._lock = lock
        return wrapper

    return decorator


def _check_threshold(label, kind, value, threshold, breach_fn, active_alerts, lock, publisher, routing_key, prefix, source):
    if threshold is None:
        return

    key = (label, kind)
    breached = breach_fn(value, threshold)

    with lock:
        was_active = active_alerts.get(key, False)

        if breached and not was_active:
            active_alerts[key] = True
            _publish(publisher, routing_key, {
                "type": "alert",
                "prefix": prefix,
                "label": label,
                "kind": kind,
                "value": round(value, 4),
                "threshold": threshold,
                "source": source,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            })
            logger.warning(
                "[%s] %s breach — label=%s value=%.4f threshold=%.4f",
                prefix, kind, label, value, threshold,
            )

        elif not breached and was_active:
            active_alerts[key] = False
            _publish(publisher, routing_key, {
                "type": "alert_cleared",
                "prefix": prefix,
                "label": label,
                "kind": kind,
                "value": round(value, 4),
                "threshold": threshold,
                "source": source,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            })
            logger.info(
                "[%s] %s cleared — label=%s value=%.4f threshold=%.4f",
                prefix, kind, label, value, threshold,
            )


def _publish(publisher, routing_key, payload):
    if publisher is None:
        return
    try:
        publisher.publish(routing_key, payload)
    except Exception:
        logger.exception("Failed to publish alert: %s", payload.get("type"))
