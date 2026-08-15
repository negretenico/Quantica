import time
from unittest.mock import MagicMock, patch

from trade.outcome_tracker import OutcomeRecord
from trade.outcome_writer import OutcomeWriter


def _make_record(symbol="BTCUSDT", pnl_pct=0.05, direction_correct=True):
    return OutcomeRecord(
        symbol=symbol,
        action="BUY",
        entry_price=100.0,
        decision_time="2026-01-01T00:00:00+00:00",
        window_seconds=60,
        outcome_price=105.0,
        pnl_pct=pnl_pct,
        direction_correct=direction_correct,
        recorded_at="2026-01-01T00:01:00+00:00",
        anomaly_score=0.8,
    )


def _mock_flush_metrics():
    return (
        patch("app.metrics.outcome_flush_total", new_callable=MagicMock),
        patch("app.metrics.outcome_flush_size", new_callable=MagicMock),
        patch("app.metrics.outcome_flush_errors_total", new_callable=MagicMock),
    )


def test_flush_on_count_threshold():
    store = MagicMock()
    with _mock_flush_metrics()[0], _mock_flush_metrics()[1], _mock_flush_metrics()[2]:
        writer = OutcomeWriter(store, flush_count=3, flush_interval_seconds=9999)
        try:
            writer.write(_make_record(symbol="A"))
            writer.write(_make_record(symbol="B"))
            assert store.write.call_count == 0
            writer.write(_make_record(symbol="C"))
            assert store.write.call_count == 3
        finally:
            writer.stop()


def test_flush_writes_all_fields():
    store = MagicMock()
    with _mock_flush_metrics()[0], _mock_flush_metrics()[1], _mock_flush_metrics()[2]:
        writer = OutcomeWriter(store, flush_count=1, flush_interval_seconds=9999)
        try:
            writer.write(_make_record())
            written = store.write.call_args[0][0]
            assert written["symbol"] == "BTCUSDT"
            assert written["pnl_pct"] == 0.05
            assert written["direction_correct"] is True
            assert written["anomaly_score"] == 0.8
            assert written["window_seconds"] == 60
        finally:
            writer.stop()


def test_manual_flush():
    store = MagicMock()
    with _mock_flush_metrics()[0], _mock_flush_metrics()[1], _mock_flush_metrics()[2]:
        writer = OutcomeWriter(store, flush_count=100, flush_interval_seconds=9999)
        try:
            writer.write(_make_record())
            assert store.write.call_count == 0
            writer.flush()
            assert store.write.call_count == 1
        finally:
            writer.stop()


def test_flush_clears_buffer():
    store = MagicMock()
    with _mock_flush_metrics()[0], _mock_flush_metrics()[1], _mock_flush_metrics()[2]:
        writer = OutcomeWriter(store, flush_count=100, flush_interval_seconds=9999)
        try:
            writer.write(_make_record())
            writer.flush()
            writer.flush()  # second flush should be a no-op
            assert store.write.call_count == 1
        finally:
            writer.stop()


def test_timer_triggers_flush():
    store = MagicMock()
    with _mock_flush_metrics()[0], _mock_flush_metrics()[1], _mock_flush_metrics()[2]:
        writer = OutcomeWriter(store, flush_count=100, flush_interval_seconds=0.1)
        try:
            writer.write(_make_record())
            assert store.write.call_count == 0
            time.sleep(0.3)
            assert store.write.call_count == 1
        finally:
            writer.stop()


def test_stop_flushes_remaining():
    store = MagicMock()
    with _mock_flush_metrics()[0], _mock_flush_metrics()[1], _mock_flush_metrics()[2]:
        writer = OutcomeWriter(store, flush_count=100, flush_interval_seconds=9999)
        writer.write(_make_record())
        writer.write(_make_record())
        writer.stop()
        assert store.write.call_count == 2


def test_store_error_does_not_crash():
    store = MagicMock()
    store.write.side_effect = IOError("disk full")
    with _mock_flush_metrics()[0], _mock_flush_metrics()[1], _mock_flush_metrics()[2]:
        writer = OutcomeWriter(store, flush_count=1, flush_interval_seconds=9999)
        try:
            writer.write(_make_record())  # should not raise
        finally:
            writer.stop()


def test_empty_flush_is_noop():
    store = MagicMock()
    with _mock_flush_metrics()[0], _mock_flush_metrics()[1], _mock_flush_metrics()[2]:
        writer = OutcomeWriter(store, flush_count=100, flush_interval_seconds=9999)
        try:
            writer.flush()
            store.write.assert_not_called()
        finally:
            writer.stop()
