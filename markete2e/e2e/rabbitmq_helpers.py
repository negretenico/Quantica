"""Temporary RabbitMQ consumer using pika for e2e tests.

Uses an exclusive auto-delete queue bound to the ``signal`` fanout exchange
so the test infrastructure never leaves orphan queues behind.
"""

import json
import threading
import time
from typing import Optional

import pika


def consume_signal_event(
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/",
    timeout_seconds: int = 30,
) -> dict:
    """Block until one message arrives on the ``signal`` fanout exchange.

    Creates an exclusive, auto-delete queue, binds it to the ``signal``
    exchange, and waits for a single message.  Returns the parsed JSON
    payload or raises ``TimeoutError``.
    """
    result_holder: dict[str, Optional[dict]] = {"message": None}
    error_holder: dict[str, Optional[Exception]] = {"error": None}
    ready_event = threading.Event()
    done_event = threading.Event()

    def _consume():
        try:
            params = pika.URLParameters(rabbitmq_url)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()

            # Declare (idempotent) the fanout exchange the producer uses
            channel.exchange_declare(
                exchange="signal",
                exchange_type="fanout",
                durable=True,
            )

            # Exclusive auto-delete queue — disappears when we disconnect
            queue_result = channel.queue_declare(
                queue="",
                exclusive=True,
                auto_delete=True,
            )
            queue_name = queue_result.method.queue

            channel.queue_bind(exchange="signal", queue=queue_name)

            def _on_message(_ch, _method, _properties, body):
                result_holder["message"] = json.loads(body)
                _ch.stop_consuming()

            channel.basic_consume(
                queue=queue_name,
                on_message_callback=_on_message,
                auto_ack=True,
            )

            # Signal that the queue is bound and we are consuming
            ready_event.set()

            # Consume with a 1-second internal timeout so we can check
            # whether the outer deadline has passed.
            deadline = time.monotonic() + timeout_seconds
            while result_holder["message"] is None:
                connection.process_data_events(time_limit=1)
                if time.monotonic() > deadline:
                    break

            channel.close()
            connection.close()
        except Exception as exc:
            error_holder["error"] = exc
        finally:
            done_event.set()

    thread = threading.Thread(target=_consume, daemon=True)
    thread.start()

    # Wait for the consumer to be ready before returning control
    ready_event.wait(timeout=timeout_seconds)

    # Wait for a message or timeout
    done_event.wait(timeout=timeout_seconds + 5)

    if error_holder["error"] is not None:
        raise error_holder["error"]

    if result_holder["message"] is None:
        raise TimeoutError(
            f"No message received on 'signal' exchange within {timeout_seconds}s"
        )

    return result_holder["message"]


class BackgroundSignalConsumer:
    """Non-blocking wrapper: starts consuming in a background thread.

    Usage::

        consumer = BackgroundSignalConsumer(rabbitmq_url, match={"symbol": "MYTEST"})
        consumer.start()          # binds queue, begins consuming
        # ... publish to Kafka ...
        event = consumer.wait()   # blocks until matching message or timeout

    The optional ``match`` dict filters incoming messages: only a message whose
    JSON payload contains all the specified key-value pairs will be returned.
    Messages that don't match are silently discarded.
    """

    def __init__(
        self,
        rabbitmq_url: str = "amqp://quantica:quantica@localhost:5672/",
        timeout_seconds: int = 30,
        match: Optional[dict] = None,
    ):
        self._rabbitmq_url = rabbitmq_url
        self._timeout_seconds = timeout_seconds
        self._match = match or {}
        self._result: Optional[dict] = None
        self._error: Optional[Exception] = None
        self._ready = threading.Event()
        self._done = threading.Event()

    def start(self) -> None:
        """Start consuming in a daemon thread. Blocks until the queue is bound."""
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()
        if not self._ready.wait(timeout=self._timeout_seconds):
            raise TimeoutError("RabbitMQ consumer failed to become ready")

    def wait(self, timeout: Optional[float] = None) -> dict:
        """Block until a matching message is received. Returns parsed JSON."""
        effective_timeout = timeout or self._timeout_seconds
        self._done.wait(timeout=effective_timeout)

        if self._error is not None:
            raise self._error
        if self._result is None:
            raise TimeoutError(
                f"No matching message on 'signal' exchange within {effective_timeout}s"
            )
        return self._result

    def _matches(self, payload: dict) -> bool:
        return all(payload.get(k) == v for k, v in self._match.items())

    def _run(self) -> None:
        try:
            params = pika.URLParameters(self._rabbitmq_url)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()

            channel.exchange_declare(
                exchange="signal",
                exchange_type="fanout",
                durable=True,
            )

            queue_result = channel.queue_declare(
                queue="",
                exclusive=True,
                auto_delete=True,
            )
            queue_name = queue_result.method.queue
            channel.queue_bind(exchange="signal", queue=queue_name)

            def _on_message(_ch, _method, _properties, body):
                payload = json.loads(body)
                if self._matches(payload):
                    self._result = payload
                    _ch.stop_consuming()

            channel.basic_consume(
                queue=queue_name,
                on_message_callback=_on_message,
                auto_ack=True,
            )

            self._ready.set()

            deadline = time.monotonic() + self._timeout_seconds
            while self._result is None:
                connection.process_data_events(time_limit=1)
                if time.monotonic() > deadline:
                    break

            channel.close()
            connection.close()
        except Exception as exc:
            self._error = exc
        finally:
            self._ready.set()  # unblock start() even on error
            self._done.set()
