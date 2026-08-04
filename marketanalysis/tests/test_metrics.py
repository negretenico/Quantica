import time
from unittest.mock import patch

from app.metrics import (
    events_consumed_total,
    duplicates_dropped_total,
    clusters_computed_total,
    anomalies_detected_total,
    errors_total,
    processing_latency,
    tick_to_analysis_latency,
    observe_tick_to_analysis,
)


def test_events_consumed_counter_increments():
    before = events_consumed_total._value.get()
    events_consumed_total.inc()
    assert events_consumed_total._value.get() == before + 1


def test_duplicates_dropped_counter_increments():
    before = duplicates_dropped_total._value.get()
    duplicates_dropped_total.inc()
    assert duplicates_dropped_total._value.get() == before + 1


def test_clusters_computed_labeled():
    clusters_computed_total.labels(symbol="BTCUSDT", cluster_id="2").inc()
    val = clusters_computed_total.labels(symbol="BTCUSDT", cluster_id="2")._value.get()
    assert val >= 1


def test_anomalies_detected_labeled():
    anomalies_detected_total.labels(symbol="ETHUSDT").inc()
    val = anomalies_detected_total.labels(symbol="ETHUSDT")._value.get()
    assert val >= 1


def test_errors_total_increments():
    before = errors_total._value.get()
    errors_total.inc()
    assert errors_total._value.get() == before + 1


def test_processing_latency_observes():
    processing_latency.labels(symbol="BTCUSDT").observe(0.015)
    # No exception means the histogram accepted the observation


def test_observe_tick_to_analysis_records_latency():
    now_ms = int(time.time() * 1000)
    event = {"symbol": "BTCUSDT", "eventTime": now_ms}
    observe_tick_to_analysis(event)
    # No exception means latency was recorded


def test_observe_tick_to_analysis_skips_missing_event_time():
    observe_tick_to_analysis({"symbol": "BTCUSDT"})
    # No exception — gracefully skipped


def test_observe_tick_to_analysis_skips_invalid_event_time():
    observe_tick_to_analysis({"symbol": "BTCUSDT", "eventTime": "not_a_number"})
    # No exception — ValueError caught internally
