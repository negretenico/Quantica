import logging
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OutcomeRecord:
    symbol: str
    action: str
    entry_price: float
    decision_time: str
    window_seconds: int
    outcome_price: float
    pnl_pct: float
    direction_correct: bool
    recorded_at: str
    anomaly_score: float = 0.0


class OutcomeTracker:
    def __init__(self, max_outcomes: int = 5000):
        self._outcomes: deque[OutcomeRecord] = deque(maxlen=max_outcomes)
        self._lock = threading.Lock()
        self._on_outcome: list[Callable[[OutcomeRecord], None]] = []

    def add_on_outcome(self, callback: Callable[[OutcomeRecord], None]) -> None:
        self._on_outcome.append(callback)

    def evaluate(self, lookback_record: dict) -> None:
        """Evaluate a raw lookback record: compute pnl and directional correctness."""
        from app.metrics import (
            outcome_tracker_total,
            outcome_tracker_correctness,
            outcome_tracker_errors_total,
        )

        try:
            symbol = lookback_record["symbol"]
            action = lookback_record["action"]
            entry_price = lookback_record["entry_price"]
            outcome_price = lookback_record["outcome_price"]
            window_seconds = lookback_record["window_seconds"]
            decision_time = lookback_record["decision_time"]
            recorded_at = lookback_record["recorded_at"]
            anomaly_score = lookback_record.get("anomaly_score", 0.0)
        except (KeyError, TypeError) as e:
            outcome_tracker_errors_total.inc()
            logger.warning("Failed to parse lookback record: %s", e)
            return

        if action == "BUY":
            pnl_pct = (outcome_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - outcome_price) / entry_price

        direction_correct = pnl_pct > 0

        rec = OutcomeRecord(
            symbol=symbol,
            action=action,
            entry_price=entry_price,
            decision_time=decision_time,
            window_seconds=window_seconds,
            outcome_price=outcome_price,
            pnl_pct=round(pnl_pct, 6),
            direction_correct=direction_correct,
            recorded_at=recorded_at,
            anomaly_score=anomaly_score,
        )

        with self._lock:
            self._outcomes.append(rec)

        for cb in self._on_outcome:
            try:
                cb(rec)
            except Exception:
                logger.exception("on_outcome callback failed")

        outcome_tracker_total.labels(
            symbol=rec.symbol,
            window=str(rec.window_seconds),
            action=rec.action,
            direction_correct=str(rec.direction_correct),
        ).inc()

        self._update_correctness_gauges(outcome_tracker_correctness)

    def _update_correctness_gauges(self, gauge) -> None:
        with self._lock:
            outcomes = list(self._outcomes)

        windows = {o.window_seconds for o in outcomes}
        actions = {o.action for o in outcomes}

        for window in windows:
            for action in actions:
                filtered = [
                    o for o in outcomes
                    if o.window_seconds == window and o.action == action
                ]
                if filtered:
                    rate = sum(o.direction_correct for o in filtered) / len(filtered)
                    gauge.labels(window=str(window), action=action).set(rate)

    def outcomes_for_symbol(self, symbol: str) -> list[OutcomeRecord]:
        with self._lock:
            return [o for o in self._outcomes if o.symbol == symbol]

    def outcomes_for_window(self, window_seconds: int) -> list[OutcomeRecord]:
        with self._lock:
            return [o for o in self._outcomes if o.window_seconds == window_seconds]

    def correctness_rate(
        self, symbol: str | None = None, window: int | None = None
    ) -> float | None:
        with self._lock:
            filtered = list(self._outcomes)

        if symbol is not None:
            filtered = [o for o in filtered if o.symbol == symbol]
        if window is not None:
            filtered = [o for o in filtered if o.window_seconds == window]

        if not filtered:
            return None

        return sum(o.direction_correct for o in filtered) / len(filtered)

    def summary(self) -> dict:
        with self._lock:
            outcomes = list(self._outcomes)

        total = len(outcomes)
        if total == 0:
            return {"total": 0, "overall_correctness": None, "by_window": {}, "by_action": {}}

        overall = sum(o.direction_correct for o in outcomes) / total

        by_window: dict[int, dict] = {}
        for w in sorted({o.window_seconds for o in outcomes}):
            w_outcomes = [o for o in outcomes if o.window_seconds == w]
            by_window[w] = {
                "total": len(w_outcomes),
                "correct": sum(o.direction_correct for o in w_outcomes),
                "rate": sum(o.direction_correct for o in w_outcomes) / len(w_outcomes),
            }

        by_action: dict[str, dict] = {}
        for a in sorted({o.action for o in outcomes}):
            a_outcomes = [o for o in outcomes if o.action == a]
            by_action[a] = {
                "total": len(a_outcomes),
                "correct": sum(o.direction_correct for o in a_outcomes),
                "rate": sum(o.direction_correct for o in a_outcomes) / len(a_outcomes),
            }

        return {
            "total": total,
            "overall_correctness": overall,
            "by_window": by_window,
            "by_action": by_action,
        }
