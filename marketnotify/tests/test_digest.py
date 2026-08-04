from unittest.mock import MagicMock, patch

from handlers.signal_counter import SignalCounter
from health.digest import HealthDigestThread
from shared.notifications import NotificationMessage
from shared.rabbitmq.consumer import ConsumerHealth


class TestHealthDigest:
    def _make_digest(self, signal_counter, consumer_health=None, targets=None):
        channel = MagicMock()
        return channel, HealthDigestThread(
            channel=channel,
            signal_counter=signal_counter,
            interval_minutes=60,
            synthesis_hour=16,
            prometheus_targets=targets or [],
            consumer_health=consumer_health,
        )

    def test_digest_shows_event_breakdown(self):
        counter = SignalCounter()
        counter.record_received()
        counter.record_received()
        counter.record_received()
        counter.record_duplicate()
        counter.record_counted()
        counter.record_counted()

        channel, digest = self._make_digest(counter)
        digest._send_digest()

        channel.send.assert_called_once()
        msg: NotificationMessage = channel.send.call_args[0][0]
        fields = dict(msg.fields)
        assert fields["Events received"] == "3"
        assert fields["Duplicates dropped"] == "1"
        assert fields["Events counted"] == "2"

    def test_digest_resets_counter(self):
        counter = SignalCounter()
        counter.record_received()
        counter.record_counted()

        channel, digest = self._make_digest(counter)
        digest._send_digest()

        snap = counter.snapshot_and_reset()
        assert snap.received == 0
        assert snap.counted == 0

    def test_digest_shows_consumer_connected(self):
        counter = SignalCounter()
        health = ConsumerHealth()
        health.set_connected(True)

        channel, digest = self._make_digest(counter, consumer_health=health)
        digest._send_digest()

        msg: NotificationMessage = channel.send.call_args[0][0]
        fields = dict(msg.fields)
        assert fields["Signal consumer"] == "CONNECTED"
        assert msg.color == "00ff00"

    def test_digest_shows_consumer_disconnected_red(self):
        counter = SignalCounter()
        health = ConsumerHealth()
        health.set_connected(False)

        channel, digest = self._make_digest(counter, consumer_health=health)
        digest._send_digest()

        msg: NotificationMessage = channel.send.call_args[0][0]
        fields = dict(msg.fields)
        assert fields["Signal consumer"] == "DISCONNECTED"
        assert msg.color == "ff0000"

    def test_digest_zero_events_with_consumer_ok(self):
        """Reproduces the reported bug: 0 events but consumer connected."""
        counter = SignalCounter()
        health = ConsumerHealth()
        health.set_connected(True)

        channel, digest = self._make_digest(counter, consumer_health=health)
        digest._send_digest()

        msg: NotificationMessage = channel.send.call_args[0][0]
        fields = dict(msg.fields)
        assert fields["Events received"] == "0"
        assert fields["Events counted"] == "0"
        assert fields["Signal consumer"] == "CONNECTED"

    @patch("health.digest.requests.get")
    def test_digest_scrapes_targets(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        counter = SignalCounter()
        channel, digest = self._make_digest(
            counter, targets=["http://localhost:8000/metrics"]
        )
        digest._send_digest()

        msg: NotificationMessage = channel.send.call_args[0][0]
        fields = dict(msg.fields)
        assert fields["localhost:8000"] == "UP"
