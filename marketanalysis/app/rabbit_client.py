import logging
from app.config import Config
from shared.rabbitmq.consumer import RabbitConsumer, ConsumerConfig

logger = logging.getLogger(__name__)


class RabbitClientManager:
    def __init__(self, config: Config):
        self.consumer = RabbitConsumer(ConsumerConfig(
            url=config.RABBITMQ_URL,
            queue=config.RABBITMQ_QUEUE,
            exchange=config.SIGNAL_EXCHANGE,
            exchange_type="fanout",
            max_retries=config.MAX_RETRIES,
            base_delay_seconds=config.RETRY_BASE_DELAY,
            dlq_enabled=True,
        ))

    def subscribe(self, handler):
        self.consumer.register_handler(handler)

    def start_consuming(self):
        self.consumer.start_consuming()
