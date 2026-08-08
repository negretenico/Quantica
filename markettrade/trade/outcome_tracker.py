import logging
import threading
from collections import deque
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

    @classmethod
    def from_lookback(cls, record: dict) -> "OutcomeRecord":
        return cls(
            symbol=record["symbol"],
            action=record["action"],
            entry_price=record["entry_price"],
            decision_time=record["decision_time"],
            window_seconds=record["window_seconds"],
            outcome_price=record["outcome_price"],
            pnl_pct=record["pnl_pct"],
            direction_correct=record["direction_correct"],
            recorded_at=record["recorded_at"],
        )


class OutcomeTracker:
    def __init__(self, max_outcomes: int = 5000):
        self._outcomes: deque[OutcomeRecord] = deque(maxlen=max_outcomes)
        self._lock = threading.Lock()

    def record_outcome(self, lookback_record: dict) -> None:
        from app.metrics import (
            outcome_tracker_total,
            outcome_tracker_correctness,
            outcome_tracker_errors_total,
        )

        try:
            rec = OutcomeRecord.from_lookback(lookback_record)
        except (KeyError, TypeError) as e:
            outcome_tracker_errors_total.inc()
            logger.warning("Failed to parse lookback record: %s", e)
            return

        with self._lock:
            self._outcomes.append(rec)

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
                    rate = sum(1 for o in filtered if o.direction_correct) / len(filtered)
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

        return sum(1 for o in filtered if o.direction_correct) / len(filtered)

    def summary(self) -> dict:
        with self._lock:
            outcomes = list(self._outcomes)

        total = len(outcomes)
        if total == 0:
            return {"total": 0, "overall_correctness": None, "by_window": {}, "by_action": {}}

        overall = sum(1 for o in outcomes if o.direction_correct) / total

        by_window: dict[int, dict] = {}
        for w in sorted({o.window_seconds for o in outcomes}):
            w_outcomes = [o for o in outcomes if o.window_seconds == w]
            by_window[w] = {
                "total": len(w_outcomes),
                "correct": sum(1 for o in w_outcomes if o.direction_correct),
                "rate": sum(1 for o in w_outcomes if o.direction_correct) / len(w_outcomes),
            }

        by_action: dict[str, dict] = {}
        for a in sorted({o.action for o in outcomes}):
            a_outcomes = [o for o in outcomes if o.action == a]
            by_action[a] = {
                "total": len(a_outcomes),
                "correct": sum(1 for o in a_outcomes if o.direction_correct),
                "rate": sum(1 for o in a_outcomes if o.direction_correct) / len(a_outcomes),
            }

        return {
            "total": total,
            "overall_correctness": overall,
            "by_window": by_window,
            "by_action": by_action,
        }
