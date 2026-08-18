import time
from unittest.mock import MagicMock, patch

import pytest

from analysis.alerter import PipelineAlerter


@pytest.fixture()
def publisher():
    return MagicMock()


@pytest.fixture()
def alerter(publisher):
    return PipelineAlerter(publisher=publisher, throttle_window=10)


class TestPipelineAlerter:
    def test_first_alert_publishes(self, alerter, publisher):
        alerter.send_alert("BTCUSDT", "validation_error", "NaN detected")
        publisher.publish.assert_called_once()
        payload = publisher.publish.call_args.kwargs["payload"]
        assert payload["type"] == "alert"
        assert payload["prefix"] == "ML_PIPELINE"
        assert payload["label"] == "BTCUSDT"
        assert payload["kind"] == "validation_error"
        assert payload["source"] == "marketanalysis"
        assert payload["detail"] == "NaN detected"

    def test_routing_key(self, alerter, publisher):
        alerter.send_alert("BTCUSDT", "ml_failure", "crash")
        assert publisher.publish.call_args.kwargs["routing_key"] == "alert.marketanalysis"

    def test_duplicate_within_window_is_throttled(self, alerter, publisher):
        alerter.send_alert("BTCUSDT", "validation_error", "NaN")
        alerter.send_alert("BTCUSDT", "validation_error", "NaN again")
        assert publisher.publish.call_count == 1

    def test_different_symbol_not_throttled(self, alerter, publisher):
        alerter.send_alert("BTCUSDT", "validation_error", "NaN")
        alerter.send_alert("ETHUSDT", "validation_error", "NaN")
        assert publisher.publish.call_count == 2

    def test_different_failure_type_not_throttled(self, alerter, publisher):
        alerter.send_alert("BTCUSDT", "validation_error", "NaN")
        alerter.send_alert("BTCUSDT", "ml_failure", "crash")
        assert publisher.publish.call_count == 2

    def test_re_fires_after_window_expires(self, alerter, publisher):
        alerter.send_alert("BTCUSDT", "validation_error", "NaN")
        # Manually expire the throttle entry
        key = ("BTCUSDT", "validation_error")
        alerter._last_alerted[key] = time.monotonic() - 20
        alerter.send_alert("BTCUSDT", "validation_error", "NaN again")
        assert publisher.publish.call_count == 2

    def test_publisher_error_does_not_propagate(self, alerter, publisher):
        publisher.publish.side_effect = RuntimeError("connection lost")
        alerter.send_alert("BTCUSDT", "ml_failure", "crash")
        # Should not raise

    def test_stale_entries_pruned(self, alerter, publisher):
        alerter.send_alert("BTCUSDT", "validation_error", "NaN")
        # Age the entry beyond 2x window
        key = ("BTCUSDT", "validation_error")
        alerter._last_alerted[key] = time.monotonic() - 30
        # A different alert triggers pruning
        alerter.send_alert("ETHUSDT", "ml_failure", "crash")
        assert key not in alerter._last_alerted
