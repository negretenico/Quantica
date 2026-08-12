"""E2E helpers for markettrade: publish to analytics exchange and poll blob output."""

import json
import glob
import os
import subprocess
import time

import pika


def publish_analytics_event(
    rabbitmq_url: str,
    payload: dict,
    exchange: str = "analytics",
    routing_key: str | None = None,
) -> None:
    """Publish a single enriched signal event to the ``analytics`` topic exchange.

    The routing key defaults to ``signal.analytics.{symbol}`` based on the
    payload's ``symbol`` field, matching the pattern markettrade binds with.
    """
    if routing_key is None:
        routing_key = f"signal.analytics.{payload.get('symbol', 'UNKNOWN')}"

    params = pika.URLParameters(rabbitmq_url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    channel.exchange_declare(
        exchange=exchange,
        exchange_type="topic",
        durable=True,
    )

    channel.basic_publish(
        exchange=exchange,
        routing_key=routing_key,
        body=json.dumps(payload),
        properties=pika.BasicProperties(delivery_mode=2),
    )

    channel.close()
    connection.close()


def poll_trade_blob(
    blob_dir: str,
    symbol: str,
    timeout_seconds: int = 30,
    poll_interval: float = 1.0,
) -> dict:
    """Poll the blob directory for a JSONL record matching *symbol*.

    Returns the first matching record or raises ``TimeoutError``.
    """
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if os.path.isdir(blob_dir):
            for path in sorted(glob.glob(os.path.join(blob_dir, "decisions_*.jsonl")), reverse=True):
                with open(path) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        record = json.loads(line)
                        if record.get("symbol") == symbol:
                            return record
        time.sleep(poll_interval)
    raise TimeoutError(
        f"No trade blob for symbol '{symbol}' in {blob_dir} within {timeout_seconds}s"
    )


def wait_for_container(
    container_name: str = "quantica-markettrade",
    timeout_seconds: int = 30,
) -> None:
    """Block until the Docker container is running."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Status}}", container_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip() == "running":
                return
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError(
        f"Container {container_name} not running after {timeout_seconds}s"
    )
