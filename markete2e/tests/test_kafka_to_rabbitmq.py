"""E2E test: Kafka order topic -> markettransformer -> RabbitMQ signal exchange.

Publishes a BinanceStreamResponse with quantity > 1,000,000 to the Kafka
``order`` topic using a unique symbol ``E2ETEST``.  markettransformer's
``LargeTradeDetected`` detector picks it up and publishes a ``SignalEvent``
to the ``signal`` fanout exchange.  A temporary pika consumer validates
the output.
"""

import uuid

import pytest

from e2e.fixtures import large_trade_event
from e2e.helpers import publish_test_event
from e2e.rabbitmq_helpers import BackgroundSignalConsumer


@pytest.mark.e2e
def test_large_trade_kafka_to_rabbitmq(
    ensure_infra,
    kafka_bootstrap,
    rabbitmq_url,
):
    """A large trade published to Kafka should produce a LARGE_TRADE SignalEvent on RabbitMQ."""

    # Use a unique symbol per run to avoid state accumulation from prior runs
    # triggering other detectors (e.g. AggressiveBuyerSeller).
    symbol = f"E2E{uuid.uuid4().hex[:8].upper()}"

    # 1. Start an ephemeral RabbitMQ consumer BEFORE publishing to Kafka.
    #    This ensures the queue is bound and ready to receive the fanout
    #    before markettransformer processes the event.
    consumer = BackgroundSignalConsumer(
        rabbitmq_url, timeout_seconds=30, match={"symbol": symbol, "type": "LARGE_TRADE"}
    )
    consumer.start()

    # 2. Build and publish a large-trade event to Kafka.
    event = large_trade_event(symbol=symbol, price="50000.00", quantity="1000001")
    metadata = publish_test_event(kafka_bootstrap, event, topic="order")
    assert metadata.topic == "order"

    # 3. Wait for the SignalEvent to arrive via RabbitMQ.
    #    Multiple signals may arrive; find the LARGE_TRADE for our symbol.
    signal = consumer.wait(timeout=30)

    # 4. Validate the SignalEvent payload.
    assert signal["symbol"] == symbol, f"Expected symbol {symbol}, got {signal.get('symbol')}"
    assert signal["type"] == "LARGE_TRADE", f"Expected type LARGE_TRADE, got {signal.get('type')}"
    assert signal["price"] == 50000.00, f"Expected price 50000.00, got {signal.get('price')}"
    assert signal["quantity"] == 1000001.0, f"Expected quantity 1000001.0, got {signal.get('quantity')}"
    assert "side" in signal, "SignalEvent missing 'side' field"
    assert signal["side"] is not None, "SignalEvent 'side' should not be None"
    assert "eventTime" in signal, "SignalEvent missing 'eventTime' field"
    assert signal["eventTime"] > 0, "SignalEvent 'eventTime' should be a positive timestamp"
    assert "reason" in signal, "SignalEvent missing 'reason' field"
    assert "1000001" in signal["reason"], (
        f"Expected reason to mention quantity, got: {signal.get('reason')}"
    )
