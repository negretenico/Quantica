import json
import logging

import pika

logger = logging.getLogger(__name__)


class RabbitPublisher:
    def __init__(self, url: str, exchange: str):
        self._url = url
        self._exchange = exchange
        self._connection = None
        self._channel = None

    def _ensure_connected(self):
        if self._channel is None or self._channel.is_closed:
            self._connection = pika.BlockingConnection(pika.URLParameters(self._url))
            self._channel = self._connection.channel()

    def publish(self, routing_key: str, payload: dict):
        self._ensure_connected()
        self._channel.basic_publish(
            exchange=self._exchange,
            routing_key=routing_key,
            body=json.dumps(payload),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        logger.debug(f"Published to {self._exchange}/{routing_key}")

    def close(self):
        if self._connection and not self._connection.is_closed:
            self._connection.close()
