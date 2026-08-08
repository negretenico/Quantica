import json

import pytest
from kafka import KafkaConsumer

from e2e.fixtures import malformed_event_missing_fields, valid_trade_event
from e2e.helpers import publish_test_event, publish_test_events, wait_for_kafka


BOOTSTRAP = "localhost:9092"
TOPIC = "order"


@pytest.mark.e2e
def test_wait_for_kafka_succeeds():
    wait_for_kafka(BOOTSTRAP, TOPIC)


@pytest.mark.e2e
def test_publish_valid_event():
    event = valid_trade_event()
    metadata = publish_test_event(BOOTSTRAP, event)
    assert metadata.topic == TOPIC
    assert metadata.partition >= 0


@pytest.mark.e2e
def test_publish_and_consume():
    event = valid_trade_event(symbol="ETHUSDT", price="3500.00", quantity="0.5")
    publish_test_event(BOOTSTRAP, event)

    # Use manual partition assignment instead of group-based subscribe to
    # avoid kafka-python-ng's selector bug on Windows during rebalance.
    from kafka import TopicPartition

    consumer = KafkaConsumer(
        bootstrap_servers=BOOTSTRAP,
        consumer_timeout_ms=10000,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        key_deserializer=lambda k: k.decode("utf-8") if k else None,
    )
    partitions = consumer.partitions_for_topic(TOPIC)
    tps = [TopicPartition(TOPIC, p) for p in partitions]
    consumer.assign(tps)
    consumer.seek_to_end(*tps)
    consumer.poll(timeout_ms=500)  # flush any buffered records after seek

    # Publish after consumer is positioned so we capture this specific event
    event2 = valid_trade_event(symbol="ETHUSDT", price="3501.00", quantity="0.25")
    publish_test_event(BOOTSTRAP, event2)

    consumed = []
    deadline = 10  # seconds
    import time
    end = time.monotonic() + deadline
    while time.monotonic() < end:
        batch = consumer.poll(timeout_ms=2000)
        for tp, records in batch.items():
            consumed.extend(records)
        if consumed:
            break

    consumer.close()
    assert len(consumed) >= 1
    assert consumed[0].value["s"] == "ETHUSDT"


@pytest.mark.e2e
def test_publish_malformed_event():
    event = malformed_event_missing_fields()
    metadata = publish_test_event(BOOTSTRAP, event)
    assert metadata.topic == TOPIC


@pytest.mark.e2e
def test_publish_batch():
    events = [valid_trade_event(symbol=s) for s in ("BTCUSDT", "ETHUSDT", "SOLUSDT")]
    results = publish_test_events(BOOTSTRAP, events)
    assert len(results) == 3
    assert all(r.topic == TOPIC for r in results)
