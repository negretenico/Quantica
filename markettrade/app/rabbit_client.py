from typing import Callable

from shared.rabbitmq.consumer import RabbitConsumer
from app.config import RabbitMQConfig


class SignalRabbitClient:
    def __init__(self, config: RabbitMQConfig):
        self._consumer = RabbitConsumer(
            url=config.URL,
            queue=config.QUEUE,
            exchange=config.EXCHANGE,
            exchange_type=config.EXCHANGE_TYPE,
            routing_key=config.ROUTING_KEY,
        )

    def subscribe(self, handler: Callable):
        self._consumer.register_handler(handler)

    def start_consuming(self):
        self._consumer.start_consuming()
