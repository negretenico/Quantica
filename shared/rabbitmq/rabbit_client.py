import logging
from rabbitmq.consumer import RabbitConsumer

logger = logging.getLogger(__name__)


class RabbitClientManager:
    def __init__(self, config):
        self._consumer = RabbitConsumer(
            url=config.RABBITMQ_URL,
            queue=config.RABBITMQ_QUEUE,
            exchange="signal",
            exchange_type="fanout",
        )

    def subscribe(self, handler):
        self._consumer.register_handler(handler)

    def start_consuming(self):
        self._consumer.start_consuming()
