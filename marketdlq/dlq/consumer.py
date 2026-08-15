import json
import time
import threading
import logging
from typing import Callable

import pika

logger = logging.getLogger(__name__)

_RETRY_DELAY = 5


class DlqConsumer:
    """Consumes from a single monitor queue bound to the DLQ exchange
    with multiple routing keys (one per source queue)."""

    def __init__(
        self,
        url: str,
        exchange: str,
        queue: str,
        routing_keys: list[str],
    ):
        self._url = url
        self._exchange = exchange
        self._queue = queue
        self._routing_keys = routing_keys
        self._handler: Callable | None = None

    def register_handler(self, handler: Callable):
        self._handler = handler

    def start_consuming(self):
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()
        logger.info("DLQ consumer thread started for queue '%s'", self._queue)

    def _run(self):
        while True:
            try:
                self._connect_and_consume()
            except pika.exceptions.AMQPConnectionError as e:
                logger.warning(
                    "RabbitMQ not available (%s), retrying in %ds", e, _RETRY_DELAY
                )
                time.sleep(_RETRY_DELAY)
            except Exception as e:
                logger.error(
                    "Unexpected DLQ consumer error (%s), retrying in %ds",
                    e,
                    _RETRY_DELAY,
                )
                time.sleep(_RETRY_DELAY)

    def _connect_and_consume(self):
        connection = pika.BlockingConnection(pika.URLParameters(self._url))
        channel = connection.channel()

        channel.exchange_declare(
            exchange=self._exchange, exchange_type="direct", durable=True
        )
        channel.queue_declare(queue=self._queue, durable=True)

        for key in self._routing_keys:
            channel.queue_bind(
                queue=self._queue, exchange=self._exchange, routing_key=key
            )
            logger.info(
                "Bound queue '%s' to exchange '%s' with routing key '%s'",
                self._queue,
                self._exchange,
                key,
            )

        def on_message(ch, method, properties, body):
            try:
                payload = json.loads(body)
            except Exception as e:
                logger.error("Failed to deserialize DLQ message: %s", e)
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            if self._handler:
                try:
                    self._handler(payload)
                except Exception as e:
                    logger.error("DLQ handler error: %s", e)

            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=self._queue, on_message_callback=on_message)
        logger.info("Waiting for DLQ messages on queue '%s'", self._queue)
        channel.start_consuming()
