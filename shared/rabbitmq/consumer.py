import json
import time
import threading
import logging
from typing import Callable

import pika

logger = logging.getLogger(__name__)

_RETRY_DELAY = 5


class RabbitConsumer:
    def __init__(self, url: str, queue: str, exchange: str = None, exchange_type: str = "fanout"):
        self._url = url
        self._queue = queue
        self._exchange = exchange
        self._exchange_type = exchange_type
        self._handler: Callable | None = None
        self._thread: threading.Thread | None = None

    def register_handler(self, handler: Callable):
        self._handler = handler

    def start_consuming(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(f"RabbitMQ consumer thread started for queue '{self._queue}'")

    def _run(self):
        while True:
            try:
                self._connect_and_consume()
            except pika.exceptions.AMQPConnectionError as e:
                logger.warning(f"RabbitMQ not available ({e}), retrying in {_RETRY_DELAY}s")
                time.sleep(_RETRY_DELAY)
            except Exception as e:
                logger.error(f"Unexpected consumer error ({e}), retrying in {_RETRY_DELAY}s")
                time.sleep(_RETRY_DELAY)

    def _connect_and_consume(self):
        connection = pika.BlockingConnection(pika.URLParameters(self._url))
        channel = connection.channel()

        if self._exchange:
            channel.exchange_declare(exchange=self._exchange, exchange_type=self._exchange_type, durable=True)

        channel.queue_declare(queue=self._queue, durable=True)

        if self._exchange:
            channel.queue_bind(queue=self._queue, exchange=self._exchange)

        def on_message(ch, method, properties, body):
            try:
                payload = json.loads(body)
                if self._handler:
                    self._handler(payload)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"Error processing message from '{self._queue}': {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=self._queue, on_message_callback=on_message)
        logger.info(f"Waiting for messages on queue '{self._queue}'")
        channel.start_consuming()
