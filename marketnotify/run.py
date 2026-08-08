import logging
import threading

from app.config import Config
from app.metrics import (
    duplicates_dropped_total,
    events_received_total,
    notifications_sent_total,
    start_metrics_server,
)
from handlers.publish_handler import PublishHandler
from handlers.signal_counter import SignalCounter
from health.digest import HealthDigestThread
from shared.dedup import DedupFilter
from shared.notifications import DiscordWebhookChannel
from shared.rabbitmq.consumer import RabbitConsumer, ConsumerConfig

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

    start_metrics_server()
    logger.info("Prometheus metrics server started on :8000")

    # --- Signal consumer (event volume counting) ---
    def handle_signal(payload):
        events_received_total.labels(queue="signal.notify").inc()
        signal_counter.record_received()
        if signal_dedup.is_duplicate(payload):
            duplicates_dropped_total.labels(queue="signal.notify").inc()
            signal_counter.record_duplicate()
            return
        signal_counter.record_counted()

    signal_consumer = RabbitConsumer(ConsumerConfig(
        url=config.RABBITMQ_URL,
        queue=config.SIGNAL_QUEUE,
        exchange=config.SIGNAL_EXCHANGE,
        exchange_type="fanout",
        max_retries=config.MAX_RETRIES,
        base_delay_seconds=config.RETRY_BASE_DELAY,
        dlq_enabled=True,
    ))
    signal_consumer.register_handler(handle_signal)
    signal_consumer.start_consuming()

    # --- Notifications consumer (publish alerts) ---
    def handle_notification(payload):
        events_received_total.labels(queue="notifications.notify").inc()
        if notify_dedup.is_duplicate(payload):
            duplicates_dropped_total.labels(queue="notifications.notify").inc()
            return
        publish_handler.handle(payload)
        notifications_sent_total.inc()

    notify_consumer = RabbitConsumer(ConsumerConfig(
        url=config.RABBITMQ_URL,
        queue=config.NOTIFY_QUEUE,
        exchange=config.NOTIFY_EXCHANGE,
        exchange_type="topic",
        routing_key="#",
        max_retries=config.MAX_RETRIES,
        base_delay_seconds=config.RETRY_BASE_DELAY,
        dlq_enabled=True,
    ))
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
        consumer_health=signal_consumer.health,
    )
    digest.start()

    logger.info("MarketNotify fully started — waiting for events")
    threading.Event().wait()


if __name__ == "__main__":
    main()
