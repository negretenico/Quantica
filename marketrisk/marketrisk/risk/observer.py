from __future__ import annotations

from datetime import datetime, timezone

from marketrisk.risk.models import NearLimitAlert


class NearLimitObserver:
    """Detects state transitions when symbol exposure crosses a near-limit threshold.

    Fires once when a symbol crosses above the threshold, then stays silent
    until the symbol drops back below. Re-fires if it crosses again.
    """

    def __init__(self, threshold_pct: float = 0.80) -> None:
        self._threshold_pct = threshold_pct
        self._active_alerts: dict[str, NearLimitAlert] = {}

    def check(self, symbol: str, current_exposure: float, max_exposure: float) -> NearLimitAlert | None:
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

        return None

    def is_near_limit(self, symbol: str) -> bool:
        return symbol in self._active_alerts

    def active_symbols(self) -> set[str]:
        return set(self._active_alerts.keys())
