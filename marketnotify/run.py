import logging
import threading

from app.config import Config
from app.metrics import (
    duplicates_dropped_total,
    events_received_total,
    notifications_failed_total,
    notifications_sent_total,
    start_metrics_server,
)
from handlers.publish_handler import PublishHandler
from handlers.signal_counter import SignalCounter
from health.digest import HealthDigestThread
from shared.dedup import DedupFilter
from shared.notifications import DiscordWebhookChannel
from shared.rabbitmq.consumer import RabbitConsumer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    config = Config()
    logger.info("Starting MarketNotify\n%s", config)

    if not config.DISCORD_WEBHOOK_URL:
        logger.warning("DISCORD_WEBHOOK_URL not set — notifications will fail")

    channel = DiscordWebhookChannel(config.DISCORD_WEBHOOK_URL)
    signal_counter = SignalCounter()
    publish_handler = PublishHandler(channel)
    signal_dedup = DedupFilter()
    notify_dedup = DedupFilter()

    # Track which errors have already been logged to avoid flooding
    _notify_errors_logged: set[str] = set()

    start_metrics_server()
    logger.info("Prometheus metrics server started on :8000")

    # --- Signal consumer (event volume counting) ---
    def handle_signal(payload):
        events_received_total.labels(queue="signal.notify").inc()
        if signal_dedup.is_duplicate(payload):
            duplicates_dropped_total.labels(queue="signal.notify").inc()
            return
        signal_counter.increment()

    signal_consumer = RabbitConsumer(
        url=config.RABBITMQ_URL,
        queue=config.SIGNAL_QUEUE,
        exchange=config.SIGNAL_EXCHANGE,
        exchange_type="fanout",
    )
    signal_consumer.register_handler(handle_signal)
    signal_consumer.start_consuming()

    # --- Notifications consumer (publish alerts) ---
    def handle_notification(payload):
        events_received_total.labels(queue="notifications.notify").inc()
        if notify_dedup.is_duplicate(payload):
            duplicates_dropped_total.labels(queue="notifications.notify").inc()
            return
        try:
            publish_handler.handle(payload)
            notifications_sent_total.inc()
        except Exception as e:
            notifications_failed_total.inc()
            error_key = str(e)
            if error_key not in _notify_errors_logged:
                logger.error("Error handling notification: %s (further duplicates suppressed)", e)
                _notify_errors_logged.add(error_key)

    notify_consumer = RabbitConsumer(
        url=config.RABBITMQ_URL,
        queue=config.NOTIFY_QUEUE,
        exchange=config.NOTIFY_EXCHANGE,
        exchange_type="topic",
        routing_key="#",
    )
    notify_consumer.register_handler(handle_notification)
    notify_consumer.start_consuming()

    # --- Background threads ---
    publish_handler.start()

    digest = HealthDigestThread(
        channel=channel,
        signal_counter=signal_counter,
        interval_minutes=config.HEALTH_DIGEST_INTERVAL_MINUTES,
        synthesis_hour=config.SYNTHESIS_HOUR,
        prometheus_targets=config.prometheus_target_list(),
    )
    digest.start()

    logger.info("MarketNotify fully started — waiting for events")
    threading.Event().wait()


if __name__ == "__main__":
    main()
