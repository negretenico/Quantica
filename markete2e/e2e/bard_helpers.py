"""E2E helpers for marketbard: publish to signal exchange and poll bard blob output."""

import json
import glob
import os
import time

import pika


def publish_signal_event(
    rabbitmq_url: str,
    payload: dict,
    exchange: str = "signal",
) -> None:
    """Publish a single signal event to the ``signal`` fanout exchange.

    This simulates what markettransformer does when it detects a signal.
    """
    params = pika.URLParameters(rabbitmq_url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    channel.exchange_declare(
        exchange=exchange,
        exchange_type="fanout",
        durable=True,
    )

    channel.basic_publish(
        exchange=exchange,
        routing_key="",
        body=json.dumps(payload),
        properties=pika.BasicProperties(delivery_mode=2),
    )

    channel.close()
    connection.close()


def poll_bard_blob(
    blob_dir: str,
    marker: str,
    timeout_seconds: int = 150,
    poll_interval: float = 2.0,
) -> dict:
    """Poll the bard blob directory for a JSONL record whose ``content`` contains *marker*.

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
                        if marker in record.get("content", ""):
                            return record
        time.sleep(poll_interval)
    raise TimeoutError(
        f"No bard blob containing '{marker}' in {blob_dir} within {timeout_seconds}s"
    )
