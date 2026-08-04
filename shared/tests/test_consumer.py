import json
from unittest.mock import patch, MagicMock, call

from shared.rabbitmq.consumer import RabbitConsumer, _DLQ_EXCHANGE


def _make_consumer(**kwargs):
    defaults = dict(url="amqp://localhost", queue="signal.trade", exchange="signal", exchange_type="fanout")
    defaults.update(kwargs)
    return RabbitConsumer(**defaults)


def _extract_on_message(mock_channel):
    """Extract the on_message_callback registered via basic_consume."""
    mock_channel.basic_consume.assert_called_once()
    return mock_channel.basic_consume.call_args[1]["on_message_callback"]


def _make_delivery(tag=1):
    method = MagicMock()
    method.delivery_tag = tag
    return method


@patch("pika.BlockingConnection")
class TestDlqDeclaration:
    def test_dlq_exchange_declared(self, mock_conn_cls):
        consumer = _make_consumer()
        mock_channel = mock_conn_cls.return_value.channel.return_value
        mock_channel.start_consuming.side_effect = KeyboardInterrupt

        try:
            consumer._connect_and_consume()
        except KeyboardInterrupt:
            pass

        exchange_calls = mock_channel.exchange_declare.call_args_list
        dlq_call = [c for c in exchange_calls if c[1].get("exchange") == _DLQ_EXCHANGE]
        assert len(dlq_call) == 1
        assert dlq_call[0][1]["exchange_type"] == "direct"
        assert dlq_call[0][1]["durable"] is True

    def test_dlq_queue_declared(self, mock_conn_cls):
        consumer = _make_consumer()
        mock_channel = mock_conn_cls.return_value.channel.return_value
        mock_channel.start_consuming.side_effect = KeyboardInterrupt

        try:
            consumer._connect_and_consume()
        except KeyboardInterrupt:
            pass

        queue_calls = mock_channel.queue_declare.call_args_list
        dlq_queue_call = [c for c in queue_calls if c[1].get("queue") == "signal.trade.dlq"]
        assert len(dlq_queue_call) == 1
        assert dlq_queue_call[0][1]["durable"] is True

    def test_dlq_queue_bound(self, mock_conn_cls):
        consumer = _make_consumer()
        mock_channel = mock_conn_cls.return_value.channel.return_value
        mock_channel.start_consuming.side_effect = KeyboardInterrupt

        try:
            consumer._connect_and_consume()
        except KeyboardInterrupt:
            pass

        bind_calls = mock_channel.queue_bind.call_args_list
        dlq_bind = [c for c in bind_calls if c[1].get("queue") == "signal.trade.dlq"]
        assert len(dlq_bind) == 1
        assert dlq_bind[0][1]["exchange"] == _DLQ_EXCHANGE
        assert dlq_bind[0][1]["routing_key"] == "signal.trade"

    def test_dlq_not_declared_when_disabled(self, mock_conn_cls):
        consumer = _make_consumer(dlq_enabled=False)
        mock_channel = mock_conn_cls.return_value.channel.return_value
        mock_channel.start_consuming.side_effect = KeyboardInterrupt

        try:
            consumer._connect_and_consume()
        except KeyboardInterrupt:
            pass

        exchange_calls = mock_channel.exchange_declare.call_args_list
        dlq_call = [c for c in exchange_calls if c[1].get("exchange") == _DLQ_EXCHANGE]
        assert len(dlq_call) == 0

        queue_calls = mock_channel.queue_declare.call_args_list
        dlq_queue = [c for c in queue_calls if c[1].get("queue") == "signal.trade.dlq"]
        assert len(dlq_queue) == 0


@patch("pika.BlockingConnection")
class TestDlqRouting:
    def test_failed_message_published_to_dlq(self, mock_conn_cls):
        consumer = _make_consumer()
        consumer.register_handler(lambda p: (_ for _ in ()).throw(ValueError("bad data")))
        mock_channel = mock_conn_cls.return_value.channel.return_value
        mock_channel.start_consuming.side_effect = KeyboardInterrupt

        try:
            consumer._connect_and_consume()
        except KeyboardInterrupt:
            pass

        on_message = _extract_on_message(mock_channel)
        delivery = _make_delivery()
        body = json.dumps({"symbol": "BTCUSDT"}).encode()

        on_message(mock_channel, delivery, None, body)

        mock_channel.basic_publish.assert_called_once()
        publish_kwargs = mock_channel.basic_publish.call_args[1]
        assert publish_kwargs["exchange"] == _DLQ_EXCHANGE
        assert publish_kwargs["routing_key"] == "signal.trade"

        envelope = json.loads(publish_kwargs["body"])
        assert envelope["original_payload"] == {"symbol": "BTCUSDT"}
        assert "ValueError" in envelope["error"]
        assert "bad data" in envelope["error"]
        assert envelope["original_queue"] == "signal.trade"
        assert envelope["attempt_count"] == 1
        assert "timestamp" in envelope

        mock_channel.basic_nack.assert_called_once_with(delivery_tag=delivery.delivery_tag, requeue=False)

    def test_successful_message_not_sent_to_dlq(self, mock_conn_cls):
        consumer = _make_consumer()
        consumer.register_handler(lambda p: None)
        mock_channel = mock_conn_cls.return_value.channel.return_value
        mock_channel.start_consuming.side_effect = KeyboardInterrupt

        try:
            consumer._connect_and_consume()
        except KeyboardInterrupt:
            pass

        on_message = _extract_on_message(mock_channel)
        delivery = _make_delivery()
        body = json.dumps({"symbol": "BTCUSDT"}).encode()

        on_message(mock_channel, delivery, None, body)

        mock_channel.basic_publish.assert_not_called()
        mock_channel.basic_ack.assert_called_once()

    def test_dlq_disabled_drops_message(self, mock_conn_cls):
        consumer = _make_consumer(dlq_enabled=False)
        consumer.register_handler(lambda p: (_ for _ in ()).throw(RuntimeError("fail")))
        mock_channel = mock_conn_cls.return_value.channel.return_value
        mock_channel.start_consuming.side_effect = KeyboardInterrupt

        try:
            consumer._connect_and_consume()
        except KeyboardInterrupt:
            pass

        on_message = _extract_on_message(mock_channel)
        delivery = _make_delivery()
        body = json.dumps({"symbol": "BTCUSDT"}).encode()

        on_message(mock_channel, delivery, None, body)

        mock_channel.basic_publish.assert_not_called()
        mock_channel.basic_nack.assert_called_once()


@patch("pika.BlockingConnection")
class TestRetries:
    def test_retries_before_dlq(self, mock_conn_cls):
        call_count = 0

        def failing_handler(p):
            nonlocal call_count
            call_count += 1
            raise ValueError("always fails")

        consumer = _make_consumer(max_retries=2)
        consumer.register_handler(failing_handler)
        mock_channel = mock_conn_cls.return_value.channel.return_value
        mock_channel.start_consuming.side_effect = KeyboardInterrupt

        try:
            consumer._connect_and_consume()
        except KeyboardInterrupt:
            pass

        on_message = _extract_on_message(mock_channel)
        delivery = _make_delivery()
        body = json.dumps({"symbol": "BTCUSDT"}).encode()

        on_message(mock_channel, delivery, None, body)

        assert call_count == 3  # 1 initial + 2 retries
        envelope = json.loads(mock_channel.basic_publish.call_args[1]["body"])
        assert envelope["attempt_count"] == 3

    def test_retry_succeeds_no_dlq(self, mock_conn_cls):
        call_count = 0

        def eventually_succeeds(p):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("transient")

        consumer = _make_consumer(max_retries=2)
        consumer.register_handler(eventually_succeeds)
        mock_channel = mock_conn_cls.return_value.channel.return_value
        mock_channel.start_consuming.side_effect = KeyboardInterrupt

        try:
            consumer._connect_and_consume()
        except KeyboardInterrupt:
            pass

        on_message = _extract_on_message(mock_channel)
        delivery = _make_delivery()
        body = json.dumps({"symbol": "BTCUSDT"}).encode()

        on_message(mock_channel, delivery, None, body)

        assert call_count == 2
        mock_channel.basic_publish.assert_not_called()
        mock_channel.basic_ack.assert_called_once()


@patch("pika.BlockingConnection")
class TestDlqMessageFormat:
    def test_malformed_json_sent_to_dlq_as_string(self, mock_conn_cls):
        consumer = _make_consumer()
        mock_channel = mock_conn_cls.return_value.channel.return_value
        mock_channel.start_consuming.side_effect = KeyboardInterrupt

        try:
            consumer._connect_and_consume()
        except KeyboardInterrupt:
            pass

        on_message = _extract_on_message(mock_channel)
        delivery = _make_delivery()
        body = b"not valid json"

        on_message(mock_channel, delivery, None, body)

        envelope = json.loads(mock_channel.basic_publish.call_args[1]["body"])
        assert envelope["original_payload"] == "not valid json"
        assert "JSONDecodeError" in envelope["error"]
        assert envelope["original_queue"] == "signal.trade"
        assert envelope["attempt_count"] == 1

    def test_no_exchange_consumer_gets_dlq(self, mock_conn_cls):
        consumer = RabbitConsumer(url="amqp://localhost", queue="my.queue")
        consumer.register_handler(lambda p: (_ for _ in ()).throw(RuntimeError("fail")))
        mock_channel = mock_conn_cls.return_value.channel.return_value
        mock_channel.start_consuming.side_effect = KeyboardInterrupt

        try:
            consumer._connect_and_consume()
        except KeyboardInterrupt:
            pass

        exchange_calls = mock_channel.exchange_declare.call_args_list
        dlq_call = [c for c in exchange_calls if c[1].get("exchange") == _DLQ_EXCHANGE]
        assert len(dlq_call) == 1

        on_message = _extract_on_message(mock_channel)
        delivery = _make_delivery()
        body = json.dumps({"data": 1}).encode()

        on_message(mock_channel, delivery, None, body)

        mock_channel.basic_publish.assert_called_once()
        assert mock_channel.basic_publish.call_args[1]["routing_key"] == "my.queue"
