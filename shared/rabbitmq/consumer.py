import json
import time
import threading
import logging
from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class QueueBinding:
    queue: str
    exchange: str | None = None
    exchange_type: str = "direct"
    routing_key: str | None = None

    def declare(self, channel):
        if self.exchange:
            channel.exchange_declare(exchange=self.exchange, exchange_type=self.exchange_type, durable=True)
        channel.queue_declare(queue=self.queue, durable=True)
        if self.exchange:
            channel.queue_bind(queue=self.queue, exchange=self.exchange, routing_key=self.routing_key)


@dataclass(frozen=True)
class ConsumerConfig:
    url: str
    queue: str
    exchange: str | None = None
    exchange_type: str = "fanout"
    routing_key: str | None = None
    max_retries: int = 0
    dlq_enabled: bool = True

    def bindings(self) -> list["QueueBinding"]:
        result = [QueueBinding(queue=self.queue, exchange=self.exchange, exchange_type=self.exchange_type, routing_key=self.routing_key)]
        if self.dlq_enabled:
            result.append(QueueBinding(queue=f"{self.queue}.dlq", exchange=_DLQ_EXCHANGE, exchange_type="direct", routing_key=self.queue))
        return result


class RabbitConsumer:
    def __init__(self, config: ConsumerConfig):
        self._config = config
        self._handler: Callable | None = None
        self._thread: threading.Thread | None = None

    def register_handler(self, handler: Callable):
        self._handler = handler

    def start_consuming(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(f"RabbitMQ consumer thread started for queue '{self._config.queue}'")

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
        cfg = self._config
        connection = pika.BlockingConnection(pika.URLParameters(cfg.url))
        channel = connection.channel()

        for binding in cfg.bindings():
            binding.declare(channel)

        def on_message(ch, method, properties, body):
            try:
                payload = json.loads(body)
            except Exception as e:
                logger.error(f"Failed to deserialize message from '{cfg.queue}': {e}")
                self._publish_to_dlq(ch, body.decode("utf-8", errors="replace"), e, 1)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return

            last_error = None
            attempts = 0
            for attempt in range(1, cfg.max_retries + 2):
                attempts = attempt
                try:
                    if self._handler:
                        self._handler(payload)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return
                except Exception as e:
                    last_error = e
                    handler_errors_total.labels(queue=cfg.queue).inc()
                    logger.error(f"Error processing message from '{cfg.queue}' (attempt {attempt}/{cfg.max_retries + 1}): {e}")
                    if attempt <= cfg.max_retries:
                        retries_total.labels(queue=cfg.queue).inc()

            self._publish_to_dlq(ch, payload, last_error, attempts)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=cfg.queue, on_message_callback=on_message)
        logger.info(f"Waiting for messages on queue '{cfg.queue}'")
        channel.start_consuming()

    def _publish_to_dlq(self, channel, original_payload, error: Exception, attempt_count: int):
        if not self._config.dlq_enabled:
            return
        queue = self._config.queue
        envelope = {
            "original_payload": original_payload,
            "error": f"{type(error).__name__}: {error}",
            "original_queue": queue,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attempt_count": attempt_count,
        }
        channel.basic_publish(
            exchange=_DLQ_EXCHANGE,
            routing_key=queue,
            body=json.dumps(envelope),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        dlq_published_total.labels(queue=queue).inc()
        logger.warning(f"Message from '{queue}' published to DLQ after {attempt_count} attempt(s): {error}")
