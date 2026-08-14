from unittest.mock import MagicMock, call

from shared.monitor import metric_monitor


def test_decorator_calls_wrapped_function():
    @metric_monitor(prefix="TEST", thresholds={"floor": 0.5})
    def fn(x):
        return {"a": (0.6, 10)}

    result = fn(42)
    assert result == {"a": (0.6, 10)}


def test_floor_breach_fires_alert():
    publisher = MagicMock()

    @metric_monitor(publisher=publisher, routing_key="alert.test", prefix="TEST", thresholds={"floor": 0.5, "min_samples": 0}, source="test")
    def fn():
        return {"bucket_a": (0.3, 10)}

    fn()
    publisher.publish.assert_called_once()
    payload = publisher.publish.call_args[0][1]
    assert payload["type"] == "alert"
    assert payload["prefix"] == "TEST"
    assert payload["label"] == "bucket_a"
    assert payload["kind"] == "floor"
    assert payload["value"] == 0.3
    assert payload["threshold"] == 0.5
    assert payload["source"] == "test"


def test_ceiling_breach_fires_alert():
    publisher = MagicMock()

    @metric_monitor(publisher=publisher, prefix="TEST", thresholds={"ceiling": 0.8, "min_samples": 0}, source="test")
    def fn():
        return {"bucket_a": (0.9, 10)}

    fn()
    payload = publisher.publish.call_args[0][1]
    assert payload["type"] == "alert"
    assert payload["kind"] == "ceiling"
    assert payload["value"] == 0.9


def test_alert_fires_only_once_until_cleared():
    publisher = MagicMock()

    @metric_monitor(publisher=publisher, prefix="TEST", thresholds={"floor": 0.5, "min_samples": 0}, source="test")
    def fn():
        return {"a": (0.3, 10)}

    fn()
    fn()
    fn()
    assert publisher.publish.call_count == 1


def test_alert_cleared_when_condition_recovers():
    publisher = MagicMock()
    current_value = [0.3]

    @metric_monitor(publisher=publisher, prefix="TEST", thresholds={"floor": 0.5, "min_samples": 0}, source="test")
    def fn():
        return {"a": (current_value[0], 10)}

    fn()  # fires alert
    assert publisher.publish.call_count == 1

    current_value[0] = 0.6  # recovers
    fn()
    assert publisher.publish.call_count == 2
    cleared_payload = publisher.publish.call_args[0][1]
    assert cleared_payload["type"] == "alert_cleared"
    assert cleared_payload["kind"] == "floor"


def test_alert_rearms_after_clear():
    publisher = MagicMock()
    current_value = [0.3]

    @metric_monitor(publisher=publisher, prefix="TEST", thresholds={"floor": 0.5, "min_samples": 0}, source="test")
    def fn():
        return {"a": (current_value[0], 10)}

    fn()  # alert
    current_value[0] = 0.6
    fn()  # cleared
    current_value[0] = 0.2
    fn()  # alert again
    assert publisher.publish.call_count == 3
    payload = publisher.publish.call_args[0][1]
    assert payload["type"] == "alert"


def test_min_samples_guard():
    publisher = MagicMock()

    @metric_monitor(publisher=publisher, prefix="TEST", thresholds={"floor": 0.5, "min_samples": 20}, source="test")
    def fn():
        return {"a": (0.1, 5)}  # only 5 samples, below min

    fn()
    publisher.publish.assert_not_called()


def test_no_publisher_still_runs_function():
    called = []

    @metric_monitor(publisher=None, prefix="TEST", thresholds={"floor": 0.5, "min_samples": 0})
    def fn():
        called.append(True)
        return {"a": (0.3, 10)}

    fn()
    assert called == [True]


def test_multiple_labels_independent():
    publisher = MagicMock()

    @metric_monitor(publisher=publisher, prefix="TEST", thresholds={"floor": 0.5, "min_samples": 0}, source="test")
    def fn():
        return {"low": (0.3, 10), "mid": (0.7, 10)}

    fn()
    assert publisher.publish.call_count == 1  # only "low" breaches
    payload = publisher.publish.call_args[0][1]
    assert payload["label"] == "low"


def test_floor_and_ceiling_independent():
    publisher = MagicMock()

    @metric_monitor(publisher=publisher, prefix="TEST", thresholds={"floor": 0.3, "ceiling": 0.9, "min_samples": 0}, source="test")
    def fn():
        return {"a": (0.95, 10)}

    fn()
    assert publisher.publish.call_count == 1
    payload = publisher.publish.call_args[0][1]
    assert payload["kind"] == "ceiling"


def test_non_dict_return_passes_through():
    @metric_monitor(prefix="TEST", thresholds={"floor": 0.5})
    def fn():
        return None

    result = fn()
    assert result is None


def test_publisher_error_does_not_propagate():
    publisher = MagicMock()
    publisher.publish.side_effect = RuntimeError("connection lost")

    @metric_monitor(publisher=publisher, prefix="TEST", thresholds={"floor": 0.5, "min_samples": 0}, source="test")
    def fn():
        return {"a": (0.3, 10)}

    # should not raise
    result = fn()
    assert result == {"a": (0.3, 10)}


def test_routing_key_passed_to_publisher():
    publisher = MagicMock()

    @metric_monitor(publisher=publisher, routing_key="alert.myservice", prefix="TEST", thresholds={"floor": 0.5, "min_samples": 0}, source="test")
    def fn():
        return {"a": (0.3, 10)}

    fn()
    assert publisher.publish.call_args[0][0] == "alert.myservice"
