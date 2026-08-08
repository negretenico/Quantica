import logging
from .consumer import RabbitConsumer, ConsumerConfig

logger = logging.getLogger(__name__)


class RabbitClientManager:
    def __init__(self, config, max_retries=3, base_delay_seconds=1.0, dlq_enabled=True):
        self._consumer = RabbitConsumer(ConsumerConfig(
            url=config.RABBITMQ_URL,
            queue=config.RABBITMQ_QUEUE,
            exchange="signal",
            exchange_type="fanout",
            max_retries=max_retries,
            base_delay_seconds=base_delay_seconds,
            dlq_enabled=dlq_enabled,
        ))

    def subscribe(self, handler):
        self._consumer.register_handler(handler)

    def start_consuming(self):
        self._consumer.start_consuming()
