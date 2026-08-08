from __future__ import annotations

import logging
from datetime import datetime, timezone

from marketrisk.risk.models import (
    ConcentrationAlert,
    ConcentrationCleared,
    ConcentrationState,
    NearLimitAlert,
    NearLimitCleared,
)

logger = logging.getLogger(__name__)


class NearLimitObserver:
    """Detects state transitions when symbol exposure crosses a near-limit threshold.

    Fires once when a symbol crosses above the threshold, then stays silent
    until the symbol drops back below. Re-fires if it crosses again.
    """

    def __init__(self, threshold_pct: float = 0.80) -> None:
        self._threshold_pct = threshold_pct
        self._active_alerts: dict[str, NearLimitAlert] = {}

    def check(self, symbol: str, current_exposure: float, max_exposure: float) -> NearLimitAlert | NearLimitCleared | None:
        if max_exposure <= 0:
            return None

        ratio = current_exposure / max_exposure

        if ratio >= self._threshold_pct and symbol not in self._active_alerts:
            alert = NearLimitAlert(
                symbol=symbol,
                current_exposure=current_exposure,
                max_exposure=max_exposure,
                ratio=ratio,
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
            )
            self._active_alerts[symbol] = alert
            return alert

        if ratio < self._threshold_pct and symbol in self._active_alerts:
            del self._active_alerts[symbol]
            return NearLimitCleared(
                symbol=symbol,
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
            )

        return None

    def is_near_limit(self, symbol: str) -> bool:
        return symbol in self._active_alerts

    def active_symbols(self) -> set[str]:
        return set(self._active_alerts.keys())

    def active_alerts(self) -> dict[str, NearLimitAlert]:
        return dict(self._active_alerts)


class ConcentrationObserver:
    """Detects when too many symbols are simultaneously in near-limit state.

    Uses a 3-state machine to manage alert lifecycle:
        ARMED → FIRED:    count crosses >= threshold, emits ConcentrationAlert
        FIRED → FIRED:    count stays >= threshold, no-op
        FIRED → DISARMED: count drops below threshold, clears alert
        DISARMED → ARMED: count stays below threshold, re-arms
        DISARMED → FIRED: count crosses >= threshold again, emits ConcentrationAlert
    """

    def __init__(self, near_limit_observer: NearLimitObserver, max_correlated: int = 3) -> None:
        self._near_limit = near_limit_observer
        self._threshold = max_correlated
        self._state = ConcentrationState.ARMED

    def check(
        self, symbol: str, current_exposure: float, max_exposure: float,
    ) -> ConcentrationAlert | ConcentrationCleared | None:
        return self._transition()

    def _transition(self) -> ConcentrationAlert | ConcentrationCleared | None:
        count = len(self._near_limit.active_symbols())

        if self._state == ConcentrationState.ARMED:
            if count >= self._threshold:
                self._state = ConcentrationState.FIRED
                alert = self._build_alert(count)
                logger.warning(
                    "Concentration risk FIRED — %d symbols at or above near-limit threshold "
                    "(threshold=%d, symbols=%s)",
                    count, self._threshold, ", ".join(alert.near_limit_symbols),
                )
                return alert

        elif self._state == ConcentrationState.FIRED:
            if count < self._threshold:
                self._state = ConcentrationState.DISARMED
                logger.info(
                    "Concentration risk DISARMED — active near-limit symbols dropped to %d "
                    "(threshold=%d)",
                    count, self._threshold,
                )
                return ConcentrationCleared(
                    remaining_count=count,
                    threshold=self._threshold,
                    timestamp_utc=datetime.now(timezone.utc).isoformat(),
                )

        elif self._state == ConcentrationState.DISARMED:
            if count >= self._threshold:
                self._state = ConcentrationState.FIRED
                alert = self._build_alert(count)
                logger.warning(
                    "Concentration risk RE-FIRED — %d symbols at or above near-limit threshold "
                    "(threshold=%d, symbols=%s)",
                    count, self._threshold, ", ".join(alert.near_limit_symbols),
                )
                return alert
            else:
                self._state = ConcentrationState.ARMED
                logger.info(
                    "Concentration risk ARMED — monitoring for threshold=%d",
                    self._threshold,
                )

        return None

    def _build_alert(self, count: int) -> ConcentrationAlert:
        alerts = self._near_limit.active_alerts()
        symbols = tuple(sorted(alerts.keys()))
        ratios = {s: alerts[s].ratio for s in symbols}
        return ConcentrationAlert(
            near_limit_symbols=symbols,
            symbol_ratios=ratios,
            count=count,
            threshold=self._threshold,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
        )

    @property
    def state(self) -> ConcentrationState:
        return self._state


class RiskObserverPipeline:
    """Runs risk observers in registration order and collects alerts.

    Observers are called sequentially so that downstream observers (e.g.
    ConcentrationObserver) can read state updated by upstream ones (e.g.
    NearLimitObserver).

    Each observer must implement check(symbol, current_exposure, max_exposure)
    and return an alert, a cleared signal, or None.
    """

    def __init__(self, observers: list) -> None:
        self._observers = list(observers)

    def check(self, symbol: str, current_exposure: float, max_exposure: float) -> list:
        alerts = []
        for observer in self._observers:
            alert = observer.check(symbol, current_exposure, max_exposure)
            if alert is not None:
                alerts.append(alert)
        return alerts
