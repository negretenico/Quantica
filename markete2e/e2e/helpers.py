import json
import subprocess
import time

import pika
from kafka import KafkaProducer


def wait_for_rabbitmq(
    rabbitmq_url: str = "amqp://quantica:quantica@localhost:5672/",
    timeout_seconds: int = 30,
) -> None:
    """Block until RabbitMQ is accepting connections."""
    deadline = time.monotonic() + timeout_seconds
    last_error = None
    while time.monotonic() < deadline:
        try:
            params = pika.URLParameters(rabbitmq_url)
            connection = pika.BlockingConnection(params)
            connection.close()
            return
        except Exception as exc:
            last_error = exc
        time.sleep(1)
    raise TimeoutError(
        f"RabbitMQ not ready at {rabbitmq_url} after {timeout_seconds}s: {last_error}"
    )


def wait_for_markettransformer(
    container_name: str = "quantica-markettransformer",
    timeout_seconds: int = 60,
) -> None:
    """Block until the markettransformer Docker container reports healthy."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Health.Status}}", container_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip() == "healthy":
                return
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError(
        f"markettransformer container not healthy after {timeout_seconds}s"
    )


def wait_for_kafka(
    bootstrap_servers: str = "localhost:9092",
    topic: str = "order",
    timeout_seconds: int = 30,
) -> None:
    """Block until Kafka broker is responsive and the topic exists."""
    deadline = time.monotonic() + timeout_seconds
    last_error = None
    while time.monotonic() < deadline:
        try:
            producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                request_timeout_ms=5000,
            )
            partitions = producer.partitions_for(topic)
            producer.close(timeout=2)
            if partitions:
                return
        except Exception as exc:
            last_error = exc
        time.sleep(1)
    raise TimeoutError(
        f"Kafka not ready at {bootstrap_servers} after {timeout_seconds}s: {last_error}"
    )


def _build_producer(bootstrap_servers: str) -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
        acks="all",
    )


def publish_test_event(
    bootstrap_servers: str,
    event: dict,
    topic: str = "order",
):
    """Publish a single BinanceStreamResponse dict to the Kafka order topic.

    Returns the RecordMetadata for assertion purposes.
    """
    producer = _build_producer(bootstrap_servers)
    try:
        future = producer.send(topic, key=event.get("s"), value=event)
        metadata = future.get(timeout=10)
        producer.flush()
        return metadata
    finally:
        producer.close(timeout=5)


def publish_test_events(
    bootstrap_servers: str,
    events: list[dict],
    topic: str = "order",
) -> list:
    """Publish multiple BinanceStreamResponse dicts. Returns list of RecordMetadata."""
    producer = _build_producer(bootstrap_servers)
    results = []
    try:
        for event in events:
            future = producer.send(topic, key=event.get("s"), value=event)
            results.append(future.get(timeout=10))
        producer.flush()
        return results
    finally:
        producer.close(timeout=5)
