import threading
from unittest.mock import MagicMock, patch

from trade.calibration import (
    BUCKET_HIGH,
    BUCKET_LOW,
    BUCKET_MID,
    CalibrationEngine,
    _bucket_for,
)
from trade.outcome_tracker import OutcomeRecord, OutcomeTracker


def _outcome(
    anomaly_score: float = 0.85,
    direction_correct: bool = True,
    symbol: str = "BTCUSDT",
) -> OutcomeRecord:
    return OutcomeRecord(
        symbol=symbol,
        action="BUY",
        entry_price=100.0,
        decision_time="2026-01-01T00:00:00+00:00",
        window_seconds=60,
        outcome_price=105.0 if direction_correct else 95.0,
        pnl_pct=0.05 if direction_correct else -0.05,
        direction_correct=direction_correct,
        recorded_at="2026-01-01T00:01:00+00:00",
        anomaly_score=anomaly_score,
    )


def _mock_calibration_metrics():
    return (
        patch("app.metrics.calibration_records_total", new_callable=MagicMock),
        patch("app.metrics.calibration_accuracy", new_callable=MagicMock),
        patch("app.metrics.calibration_window_size", new_callable=MagicMock),
    )


# --- Bucketing logic ---


def test_score_0_7_lands_in_low_bucket():
    assert _bucket_for(0.7) == BUCKET_LOW


def test_score_0_79_lands_in_low_bucket():
    assert _bucket_for(0.79) == BUCKET_LOW


def test_score_0_8_lands_in_mid_bucket():
    assert _bucket_for(0.8) == BUCKET_MID


def test_score_0_9_lands_in_high_bucket():
    assert _bucket_for(0.9) == BUCKET_HIGH


def test_score_1_0_lands_in_high_bucket():
    assert _bucket_for(1.0) == BUCKET_HIGH


def test_score_below_0_7_has_no_bucket():
    assert _bucket_for(0.65) is None


# --- Accuracy computation ---


def test_accuracy_all_correct():
    with _mock_calibration_metrics()[0], _mock_calibration_metrics()[1], _mock_calibration_metrics()[2]:
        engine = CalibrationEngine()
        for _ in range(3):
            engine.record(_outcome(direction_correct=True))
        assert engine.accuracy() == 1.0


def test_accuracy_all_incorrect():
    with _mock_calibration_metrics()[0], _mock_calibration_metrics()[1], _mock_calibration_metrics()[2]:
        engine = CalibrationEngine()
        for _ in range(3):
            engine.record(_outcome(direction_correct=False))
        assert engine.accuracy() == 0.0


def test_accuracy_mixed():
    with _mock_calibration_metrics()[0], _mock_calibration_metrics()[1], _mock_calibration_metrics()[2]:
        engine = CalibrationEngine()
        engine.record(_outcome(direction_correct=True))
        engine.record(_outcome(direction_correct=True))
        engine.record(_outcome(direction_correct=False))
        engine.record(_outcome(direction_correct=False))
        assert engine.accuracy() == 0.5


def test_accuracy_per_bucket():
    with _mock_calibration_metrics()[0], _mock_calibration_metrics()[1], _mock_calibration_metrics()[2]:
        engine = CalibrationEngine()
        engine.record(_outcome(anomaly_score=0.75, direction_correct=True))
        engine.record(_outcome(anomaly_score=0.75, direction_correct=False))
        engine.record(_outcome(anomaly_score=0.85, direction_correct=True))
        engine.record(_outcome(anomaly_score=0.85, direction_correct=True))
        engine.record(_outcome(anomaly_score=0.95, direction_correct=False))

        assert engine.accuracy(BUCKET_LOW) == 0.5
        assert engine.accuracy(BUCKET_MID) == 1.0
        assert engine.accuracy(BUCKET_HIGH) == 0.0


def test_overall_accuracy_across_buckets():
    with _mock_calibration_metrics()[0], _mock_calibration_metrics()[1], _mock_calibration_metrics()[2]:
        engine = CalibrationEngine()
        engine.record(_outcome(anomaly_score=0.75, direction_correct=True))
        engine.record(_outcome(anomaly_score=0.85, direction_correct=True))
        engine.record(_outcome(anomaly_score=0.95, direction_correct=False))
        # 2 correct out of 3
        assert abs(engine.accuracy() - 2 / 3) < 1e-9


# --- Edge cases ---


def test_accuracy_empty_engine():
    engine = CalibrationEngine()
    assert engine.accuracy() is None


def test_accuracy_empty_bucket():
    with _mock_calibration_metrics()[0], _mock_calibration_metrics()[1], _mock_calibration_metrics()[2]:
        engine = CalibrationEngine()
        engine.record(_outcome(anomaly_score=0.85))
        assert engine.accuracy(BUCKET_LOW) is None
        assert engine.accuracy(BUCKET_HIGH) is None


def test_rolling_window_evicts_oldest():
    with _mock_calibration_metrics()[0], _mock_calibration_metrics()[1], _mock_calibration_metrics()[2]:
        engine = CalibrationEngine(window_size=5)
        for i in range(6):
            engine.record(_outcome(symbol=f"SYM{i}"))
        summary = engine.summary()
        assert summary["total"] == 5


def test_rolling_window_default_200():
    engine = CalibrationEngine()
    assert engine._window_size == 200


def test_summary_structure():
    with _mock_calibration_metrics()[0], _mock_calibration_metrics()[1], _mock_calibration_metrics()[2]:
        engine = CalibrationEngine()
        engine.record(_outcome(anomaly_score=0.75, direction_correct=True))
        engine.record(_outcome(anomaly_score=0.85, direction_correct=False))

        summary = engine.summary()
        assert summary["window_size"] == 200
        assert summary["total"] == 2
        assert "[0.7, 0.8)" in summary["buckets"]
        assert "[0.8, 0.9)" in summary["buckets"]
        assert "[0.9, 1.0]" in summary["buckets"]
        assert summary["buckets"]["[0.7, 0.8)"]["total"] == 1
        assert summary["buckets"]["[0.7, 0.8)"]["correct"] == 1
        assert summary["buckets"]["[0.7, 0.8)"]["accuracy"] == 1.0
        assert summary["buckets"]["[0.8, 0.9)"]["total"] == 1
        assert summary["buckets"]["[0.8, 0.9)"]["correct"] == 0
        assert summary["buckets"]["[0.8, 0.9)"]["accuracy"] == 0.0
        assert summary["overall_accuracy"] == 0.5


def test_summary_empty():
    engine = CalibrationEngine()
    summary = engine.summary()
    assert summary["total"] == 0
    assert summary["overall_accuracy"] is None
    for bucket_data in summary["buckets"].values():
        assert bucket_data["total"] == 0
        assert bucket_data["correct"] == 0
        assert bucket_data["accuracy"] is None


# --- Thread safety ---


def test_concurrent_record_calls():
    with _mock_calibration_metrics()[0], _mock_calibration_metrics()[1], _mock_calibration_metrics()[2]:
        engine = CalibrationEngine(window_size=1000)
        threads = []
        for _ in range(10):
            t = threading.Thread(
                target=lambda: [engine.record(_outcome()) for _ in range(50)]
            )
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        assert engine.summary()["total"] == 500


# --- Integration with OutcomeTracker callback ---


def _mock_tracker_metrics():
    return (
        patch("app.metrics.outcome_tracker_total", new_callable=MagicMock),
        patch("app.metrics.outcome_tracker_correctness", new_callable=MagicMock),
        patch("app.metrics.outcome_tracker_errors_total", new_callable=MagicMock),
    )


def test_calibration_receives_outcome_from_tracker_callback():
    with _mock_tracker_metrics()[0], _mock_tracker_metrics()[1], _mock_tracker_metrics()[2], \
         _mock_calibration_metrics()[0], _mock_calibration_metrics()[1], _mock_calibration_metrics()[2]:
        tracker = OutcomeTracker()
        engine = CalibrationEngine()
        tracker.add_on_outcome(engine.record)

        tracker.evaluate({
            "type": "price_lookback",
            "symbol": "BTCUSDT",
            "action": "BUY",
            "entry_price": 100.0,
            "decision_time": "2026-01-01T00:00:00+00:00",
            "window_seconds": 60,
            "outcome_price": 105.0,
            "recorded_at": "2026-01-01T00:01:00+00:00",
            "anomaly_score": 0.85,
        })

        assert engine.summary()["total"] == 1
        assert engine.accuracy(BUCKET_MID) == 1.0
