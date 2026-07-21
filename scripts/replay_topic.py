"""
replay_topic.py — Replay a JSONL dump into a Kafka topic at a configurable speed multiplier.

The script drives inter-event timing from the `E` (eventTime) field in each record.
It does NOT use a simple loop — it computes the exact target delay between consecutive
messages and sleeps accordingly, adjusted by the speed multiplier.

Measurement: every 1000 messages, the script logs actual vs target inter-event delay.
In a second background thread, kafka consumer-group lag (records-lag-max) for the
markettransformer consumer group and RabbitMQ queue depth are polled every second and
written to a separate metrics log file alongside stdout.

Usage:
    python scripts/replay_topic.py \\
        --file dump/order_20250719_1Hours.jsonl \\
        --speed 10 \\
        --topic order-replay \\
        [--bootstrap localhost:9092] \\
        [--consumer-group market-transformer-group] \\
        [--rabbitmq-api http://guest:guest@localhost:15672]

Speed 1 produces at real-time pace (useful as the 1x baseline).

Headers forwarded per message (if kafka-python-ng version supports them):
    x-binance-event-time  — original E field (ms epoch, bytes)
    x-binance-trade-time  — original T field (ms epoch, bytes)
"""

import argparse
import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from kafka import KafkaProducer
from kafka.admin import KafkaAdminClient
from kafka.errors import KafkaError

import urllib.request
import urllib.parse
import base64


# ---------------------------------------------------------------------------
# Kafka producer
# ---------------------------------------------------------------------------

def build_producer(bootstrap: str) -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=bootstrap,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
        acks=1,
        linger_ms=5,
        compression_type=None,
    )


# ---------------------------------------------------------------------------
# Lag measurement helpers
# ---------------------------------------------------------------------------

def poll_kafka_lag(bootstrap: str, consumer_group: str) -> int | None:
    """
    Returns records-lag-max across all partitions for the given consumer group,
    or None if it cannot be determined.
    Uses KafkaAdminClient directly — no Actuator dependency.
    """
    try:
        admin = KafkaAdminClient(bootstrap_servers=bootstrap, client_id="replay-lag-poller")
        offsets = admin.list_consumer_group_offsets(consumer_group)
        admin.close()
        if not offsets:
            return None
        # offsets maps TopicPartition -> OffsetAndMetadata; we need end offsets too
        # KafkaAdminClient does not expose end offsets directly; use KafkaConsumer for that.
        from kafka import KafkaConsumer, TopicPartition
        tmp = KafkaConsumer(bootstrap_servers=bootstrap, enable_auto_commit=False)
        end_offsets = tmp.end_offsets(list(offsets.keys()))
        tmp.close()
        max_lag = max(
            (end_offsets.get(tp, committed.offset) - committed.offset)
            for tp, committed in offsets.items()
            if committed.offset >= 0
        )
        return max(max_lag, 0)
    except Exception:
        return None


def poll_rabbitmq_depth(rabbitmq_api: str | None) -> int | None:
    """
    Fetches total message count across all queues from RabbitMQ management API.
    rabbitmq_api should be e.g. http://guest:guest@localhost:15672
    Returns None if unavailable.
    """
    if not rabbitmq_api:
        return None
    try:
        parsed = urllib.parse.urlparse(rabbitmq_api)
        base = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
        url = base.rstrip("/") + "/api/queues"
        credentials = base64.b64encode(
            f"{parsed.username}:{parsed.password}".encode()
        ).decode()
        req = urllib.request.Request(url, headers={"Authorization": f"Basic {credentials}"})
        with urllib.request.urlopen(req, timeout=2) as resp:
            queues = json.loads(resp.read().decode("utf-8"))
        return sum(q.get("messages", 0) for q in queues)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Background metrics thread
# ---------------------------------------------------------------------------

class MetricsPoller(threading.Thread):
    def __init__(
        self,
        bootstrap: str,
        consumer_group: str,
        rabbitmq_api: str | None,
        metrics_log_path: str,
        stop_event: threading.Event,
    ):
        super().__init__(daemon=True, name="metrics-poller")
        self.bootstrap = bootstrap
        self.consumer_group = consumer_group
        self.rabbitmq_api = rabbitmq_api
        self.metrics_log_path = metrics_log_path
        self.stop_event = stop_event

    def run(self) -> None:
        with open(self.metrics_log_path, "w", encoding="utf-8") as fh:
            fh.write("timestamp_utc,records_lag_max,rabbitmq_total_messages\n")
            fh.flush()
            while not self.stop_event.is_set():
                lag = poll_kafka_lag(self.bootstrap, self.consumer_group)
                depth = poll_rabbitmq_depth(self.rabbitmq_api)
                ts = datetime.now(timezone.utc).isoformat()
                line = f"{ts},{lag if lag is not None else ''},{depth if depth is not None else ''}"
                fh.write(line + "\n")
                fh.flush()
                print(f"[metrics] {ts} lag={lag} rmq_depth={depth}", flush=True)
                self.stop_event.wait(timeout=1.0)


# ---------------------------------------------------------------------------
# Replay loop
# ---------------------------------------------------------------------------

def replay(
    file_path: str,
    speed: float,
    topic: str,
    bootstrap: str,
    consumer_group: str,
    rabbitmq_api: str | None,
) -> None:
    p = Path(file_path)
    if not p.exists():
        print(f"ERROR: dump file not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    stem = p.stem
    metrics_log = str(p.parent / f"{stem}_speed{int(speed)}x_metrics.csv")
    print(f"Replay file  : {file_path}", flush=True)
    print(f"Target topic : {topic}", flush=True)
    print(f"Speed        : {speed}x", flush=True)
    print(f"Bootstrap    : {bootstrap}", flush=True)
    print(f"Metrics log  : {metrics_log}", flush=True)

    try:
        producer = build_producer(bootstrap)
    except KafkaError as exc:
        print(f"ERROR: Could not connect to Kafka: {exc}", file=sys.stderr)
        sys.exit(1)

    stop_event = threading.Event()
    poller = MetricsPoller(bootstrap, consumer_group, rabbitmq_api, metrics_log, stop_event)
    poller.start()

    count = 0
    prev_event_time: int | None = None
    total_target_delay_ms = 0.0
    total_actual_delay_ms = 0.0
    batch_target_delay_ms = 0.0
    batch_actual_delay_ms = 0.0
    wall_prev = time.monotonic()

    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            for raw_line in fh:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue

                payload = json.loads(raw_line)
                # Strip the dump-time marker before replaying
                payload.pop("_ingested_at", None)

                event_time: int = payload.get("E", 0)
                trade_time: int = payload.get("T", 0)

                # Compute and apply inter-event delay
                if prev_event_time is not None and event_time and prev_event_time:
                    raw_delta_ms = max(event_time - prev_event_time, 0)
                    target_sleep_s = (raw_delta_ms / speed) / 1000.0
                    if target_sleep_s > 0:
                        time.sleep(target_sleep_s)
                    target_delay_ms = raw_delta_ms / speed
                else:
                    target_delay_ms = 0.0

                wall_now = time.monotonic()
                actual_delay_ms = (wall_now - wall_prev) * 1000.0
                wall_prev = wall_now

                if prev_event_time is not None:
                    total_target_delay_ms += target_delay_ms
                    total_actual_delay_ms += actual_delay_ms
                    batch_target_delay_ms += target_delay_ms
                    batch_actual_delay_ms += actual_delay_ms

                # Build headers — forward original Binance timestamps
                headers = []
                if event_time:
                    headers.append(("x-binance-event-time", str(event_time).encode()))
                if trade_time:
                    headers.append(("x-binance-trade-time", str(trade_time).encode()))

                symbol: str = payload.get("s", "")
                try:
                    producer.send(topic, key=symbol or None, value=payload, headers=headers)
                except KafkaError as exc:
                    print(f"WARN: send failed at message {count}: {exc}", flush=True)

                count += 1
                prev_event_time = event_time

                if count % 1000 == 0:
                    avg_target = batch_target_delay_ms / 1000.0
                    avg_actual = batch_actual_delay_ms / 1000.0
                    drift_pct = ((avg_actual - avg_target) / avg_target * 100) if avg_target > 0 else 0.0
                    print(
                        f"[replay] msg={count:,} | "
                        f"avg_target_delay={avg_target:.2f}ms | "
                        f"avg_actual_delay={avg_actual:.2f}ms | "
                        f"drift={drift_pct:+.1f}%",
                        flush=True,
                    )
                    batch_target_delay_ms = 0.0
                    batch_actual_delay_ms = 0.0

    except KeyboardInterrupt:
        print("\nInterrupted by user.", flush=True)
    finally:
        producer.flush()
        producer.close()
        stop_event.set()
        poller.join(timeout=3)

    overall_drift = (
        ((total_actual_delay_ms - total_target_delay_ms) / total_target_delay_ms * 100)
        if total_target_delay_ms > 0
        else 0.0
    )
    print(f"\nReplay complete. {count:,} messages produced.", flush=True)
    print(
        f"Overall timing: target={total_target_delay_ms / 1000:.1f}s "
        f"actual={total_actual_delay_ms / 1000:.1f}s "
        f"drift={overall_drift:+.1f}%",
        flush=True,
    )
    print(f"Metrics written to: {metrics_log}", flush=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Replay a JSONL order dump into Kafka at speed")
    parser.add_argument("--file", required=True, help="Path to the JSONL dump file")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Speed multiplier (e.g. 10, 50, 100). Default: 1 (real-time baseline)")
    parser.add_argument("--topic", default="order",
                        help="Target Kafka topic (default: order)")
    parser.add_argument("--bootstrap", default="localhost:9092",
                        help="Kafka bootstrap servers (default: localhost:9092)")
    parser.add_argument("--consumer-group", default="market-transformer-group",
                        help="Consumer group to measure lag against (default: market-transformer-group)")
    parser.add_argument("--rabbitmq-api", default=None,
                        help="RabbitMQ management base URL e.g. http://guest:guest@localhost:15672 (optional)")
    args = parser.parse_args()

    replay(
        file_path=args.file,
        speed=args.speed,
        topic=args.topic,
        bootstrap=args.bootstrap,
        consumer_group=args.consumer_group,
        rabbitmq_api=args.rabbitmq_api,
    )


if __name__ == "__main__":
    main()
