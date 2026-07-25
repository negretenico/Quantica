import json
from unittest.mock import MagicMock, patch, call

from shared.rabbitmq.consumer import RabbitConsumer


def _make_consumer():
    return RabbitConsumer(
        url="amqp://guest:guest@localhost/",
        queue="signal.trade",
        exchange="analytics",
        exchange_type="topic",
        routing_key="signal.analytics.#",
    )


@patch("pika.BlockingConnection")
def test_exchange_declare(mock_connection_cls):
    mock_channel = MagicMock()
    mock_connection_cls.return_value.channel.return_value = mock_channel

    consumer = _make_consumer()
    consumer._connect_and_consume()

    mock_channel.exchange_declare.assert_called_once_with(
        exchange="analytics",
        exchange_type="topic",
        durable=True,
    )


@patch("pika.BlockingConnection")
def test_queue_bind_routing_key(mock_connection_cls):
    mock_channel = MagicMock()
    mock_connection_cls.return_value.channel.return_value = mock_channel

    consumer = _make_consumer()
    consumer._connect_and_consume()

    mock_channel.queue_bind.assert_called_once_with(
        queue="signal.trade",
        exchange="analytics",
        routing_key="signal.analytics.#",
    )


@patch("pika.BlockingConnection")
def test_handler_called_on_message(mock_connection_cls):
    mock_channel = MagicMock()
    mock_connection_cls.return_value.channel.return_value = mock_channel

    consumer = _make_consumer()
    handler = MagicMock()
    consumer.register_handler(handler)
    consumer._connect_and_consume()

    # Capture the on_message callback registered with basic_consume
    on_message = mock_channel.basic_consume.call_args.kwargs["on_message_callback"]

    mock_method = MagicMock()
    mock_method.delivery_tag = 42
    payload = {"symbol": "BTCUSDT", "anomaly_score": 0.9}

    on_message(mock_channel, mock_method, None, json.dumps(payload).encode())

    handler.assert_called_once_with(payload)
    mock_channel.basic_ack.assert_called_once_with(delivery_tag=42)
