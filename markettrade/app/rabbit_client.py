from typing import Callable

from shared.rabbitmq.consumer import RabbitConsumer
from app.config import RabbitMQConfig


class SignalRabbitClient:
    def __init__(self, config: RabbitMQConfig):
        self._consumer = RabbitConsumer(
            url=config.URL,
            queue=config.QUEUE,
            exchange=config.SIGNAL_EXCHANGE,
            exchange_type="fanout",
        )

    def subscribe(self, handler: Callable):
        self._consumer.register_handler(handler)

    def start_consuming(self):
        self._consumer.start_consuming()
