"""
dump_topic.py — Read from the Kafka `order` topic and write records to a JSONL dump file.

Output filename: dump/order_YYYYMMDD_<N>Hours.jsonl
Each line is a JSON object with an added "_ingested_at" key (wall-clock ms at dump time)
so that the dump does not destroy the original eventTime/tradeTime fields.

Usage:
    python scripts/dump_topic.py [--topic order] [--hours 1] [--bootstrap localhost:9092]

The script reads from the beginning of the topic and exits after consuming
`--hours` worth of data (measured by eventTime span in the records, not wall clock).
If --hours is omitted it runs until interrupted (Ctrl-C).
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

from kafka import KafkaConsumer
from kafka.errors import KafkaError

DUMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dump")


def build_consumer(bootstrap: str, topic: str) -> KafkaConsumer:
    return KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        group_id=None,  # no group — pure read-from-beginning, no offset commit
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        consumer_timeout_ms=10_000,
        value_deserializer=lambda x: json.loads(x.decode("utf-8")) if x else None,
        key_deserializer=lambda x: x.decode("utf-8") if x else None,
    )


def output_path(hours: float | None) -> str:
    os.makedirs(DUMP_DIR, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d")
    hours_tag = f"{int(hours)}Hours" if hours else "unbounded"
    return os.path.join(DUMP_DIR, f"order_{date_tag}_{hours_tag}.jsonl")


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump Kafka order topic to JSONL")
    parser.add_argument("--topic", default="order", help="Kafka topic to dump (default: order)")
    parser.add_argument("--hours", type=float, default=None,
                        help="Stop after this many hours of eventTime span (default: run until Ctrl-C)")
    parser.add_argument("--bootstrap", default="localhost:9092", help="Kafka bootstrap servers")
    args = parser.parse_args()

    out_path = output_path(args.hours)
    span_ms = int(args.hours * 3_600_000) if args.hours else None

    print(f"Dumping topic '{args.topic}' -> {out_path}", flush=True)
    if span_ms:
        print(f"Will stop after {args.hours} hour(s) of eventTime span.", flush=True)

    try:
        consumer = build_consumer(args.bootstrap, args.topic)
    except KafkaError as exc:
        print(f"ERROR: Could not connect to Kafka: {exc}", file=sys.stderr)
        sys.exit(1)

    first_event_time: int | None = None
    count = 0

    try:
        with open(out_path, "w", encoding="utf-8") as fh:
            for message in consumer:
                payload = message.value
                if payload is None:
                    continue

                payload["_ingested_at"] = int(time.time() * 1000)

                fh.write(json.dumps(payload) + "\n")
                count += 1

                event_time: int = payload.get("E", 0)

                if first_event_time is None and event_time:
                    first_event_time = event_time

                if count % 10_000 == 0:
                    elapsed_ms = (event_time - first_event_time) if first_event_time else 0
                    print(
                        f"  {count:,} messages | eventTime span: {elapsed_ms / 1000:.1f}s",
                        flush=True,
                    )

                if span_ms and first_event_time and event_time - first_event_time >= span_ms:
                    print(f"Reached {args.hours}h of eventTime span. Stopping.", flush=True)
                    break

    except KeyboardInterrupt:
        print("\nInterrupted by user.", flush=True)
    finally:
        consumer.close()

    print(f"Done. {count:,} messages written to {out_path}", flush=True)


if __name__ == "__main__":
    main()
