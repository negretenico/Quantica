import logging
import threading
from collections import deque

from trade.outcome_tracker import OutcomeRecord

logger = logging.getLogger(__name__)

BUCKET_LOW = (0.7, 0.8)
BUCKET_MID = (0.8, 0.9)
BUCKET_HIGH = (0.9, 1.0)
BUCKETS = [BUCKET_LOW, BUCKET_MID, BUCKET_HIGH]


def _bucket_label(bucket: tuple[float, float]) -> str:
    low, high = bucket
    close = "]" if high == 1.0 else ")"
    return f"[{low}, {high}{close}"


def _bucket_for(anomaly_score: float) -> tuple[float, float] | None:
    for low, high in BUCKETS:
        if high == 1.0:
            if low <= anomaly_score <= high:
                return (low, high)
        else:
            if low <= anomaly_score < high:
                return (low, high)
    return None


class CalibrationEngine:
    def __init__(self, window_size: int = 200):
        self._window_size = window_size
        self._outcomes: deque[OutcomeRecord] = deque(maxlen=window_size)
        self._lock = threading.Lock()

    def record(self, outcome: OutcomeRecord) -> None:
        from app.metrics import (
            calibration_records_total,
            calibration_accuracy,
            calibration_window_size,
        )

        bucket = _bucket_for(outcome.anomaly_score)
        label = _bucket_label(bucket) if bucket else "none"

        with self._lock:
            self._outcomes.append(outcome)

        calibration_records_total.labels(bucket=label).inc()
        calibration_window_size.set(len(self._outcomes))

        for b in BUCKETS:
            acc = self.accuracy(b)
            if acc is not None:
                calibration_accuracy.labels(bucket=_bucket_label(b)).set(acc)

    def count(self, bucket: tuple[float, float] | None = None) -> int:
        with self._lock:
            outcomes = list(self._outcomes)

        if bucket is not None:
            outcomes = [o for o in outcomes if _bucket_for(o.anomaly_score) == bucket]

        return len(outcomes)

    def accuracy(self, bucket: tuple[float, float] | None = None) -> float | None:
        with self._lock:
            outcomes = list(self._outcomes)

        if bucket is not None:
            outcomes = [o for o in outcomes if _bucket_for(o.anomaly_score) == bucket]

        if not outcomes:
            return None

        return sum(o.direction_correct for o in outcomes) / len(outcomes)

    def summary(self) -> dict:
        with self._lock:
            outcomes = list(self._outcomes)

        total = len(outcomes)
        overall = sum(o.direction_correct for o in outcomes) / total if total else None

        buckets_summary = {}
        for b in BUCKETS:
            filtered = [o for o in outcomes if _bucket_for(o.anomaly_score) == b]
            count = len(filtered)
            correct = sum(o.direction_correct for o in filtered)
            buckets_summary[_bucket_label(b)] = {
                "total": count,
                "correct": correct,
                "accuracy": correct / count if count else None,
            }

        return {
            "window_size": self._window_size,
            "total": total,
            "buckets": buckets_summary,
            "overall_accuracy": overall,
        }
