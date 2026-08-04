import json
import time
import threading
import logging
from datetime import datetime, timezone
from typing import Callable

import pika
from prometheus_client import Counter

logger = logging.getLogger(__name__)

_RETRY_DELAY = 5
_DLQ_EXCHANGE = "dlq"

dlq_published_total = Counter(
    "rabbitmq_consumer_dlq_published_total",
    "Messages published to dead-letter queue",
    ["queue"],
)
retries_total = Counter(
    "rabbitmq_consumer_retries_total",
    "Retry attempts before dead-letter",
    ["queue"],
)
handler_errors_total = Counter(
    "rabbitmq_consumer_handler_errors_total",
    "Total handler errors (includes retried and dead-lettered)",
    ["queue"],
)


class RabbitConsumer:
    def __init__(self, url: str, queue: str, exchange: str = None, exchange_type: str = "fanout",
                 routing_key: str = None, max_retries: int = 0, dlq_enabled: bool = True):
        self._url = url
        self._queue = queue
        self._exchange = exchange
        self._exchange_type = exchange_type
        self._routing_key = routing_key
        self._max_retries = max_retries
        self._dlq_enabled = dlq_enabled
        self._handler: Callable | None = None
        self._thread: threading.Thread | None = None

    @property
    def dlq_queue(self) -> str:
        return f"{self._queue}.dlq"

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
            channel.queue_bind(queue=self._queue, exchange=self._exchange, routing_key=self._routing_key)

        if self._dlq_enabled:
            channel.exchange_declare(exchange=_DLQ_EXCHANGE, exchange_type="direct", durable=True)
            channel.queue_declare(queue=self.dlq_queue, durable=True)
            channel.queue_bind(queue=self.dlq_queue, exchange=_DLQ_EXCHANGE, routing_key=self._queue)

        def on_message(ch, method, properties, body):
            try:
                payload = json.loads(body)
            except Exception as e:
                logger.error(f"Failed to deserialize message from '{self._queue}': {e}")
                self._publish_to_dlq(ch, body.decode("utf-8", errors="replace"), e, 1)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return

            last_error = None
            attempts = 0
            for attempt in range(1, self._max_retries + 2):
                attempts = attempt
                try:
                    if self._handler:
                        self._handler(payload)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return
                except Exception as e:
                    last_error = e
                    handler_errors_total.labels(queue=self._queue).inc()
                    logger.error(f"Error processing message from '{self._queue}' (attempt {attempt}/{self._max_retries + 1}): {e}")
                    if attempt <= self._max_retries:
                        retries_total.labels(queue=self._queue).inc()

            self._publish_to_dlq(ch, payload, last_error, attempts)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=self._queue, on_message_callback=on_message)
        logger.info(f"Waiting for messages on queue '{self._queue}'")
        channel.start_consuming()

    def _publish_to_dlq(self, channel, original_payload, error: Exception, attempt_count: int):
        if not self._dlq_enabled:
            return
        envelope = {
            "original_payload": original_payload,
            "error": f"{type(error).__name__}: {error}",
            "original_queue": self._queue,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attempt_count": attempt_count,
        }
        channel.basic_publish(
            exchange=_DLQ_EXCHANGE,
            routing_key=self._queue,
            body=json.dumps(envelope),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        dlq_published_total.labels(queue=self._queue).inc()
        logger.warning(f"Message from '{self._queue}' published to DLQ after {attempt_count} attempt(s): {error}")
