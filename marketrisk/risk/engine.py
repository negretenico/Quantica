from __future__ import annotations

from app.config import Config
from marketrisk.risk.models import ProposedAction, RiskDecision


class RiskEngine:
    """Evaluates proposed actions against per-trade and per-symbol risk caps.

    Note: _symbol_exposure is not thread-safe. This engine is intended for
    single-threaded use within the markettrade worker process.
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._symbol_exposure: dict[str, float] = {}

    def evaluate(self, action: ProposedAction) -> RiskDecision:
        if action.raw_quantity > self._config.MAX_TRADE_QUANTITY:
            return RiskDecision(
                approved=False,
                sized_quantity=None,
                rejection_reason="EXCEEDS_TRADE_CAP",
            )

        current_exposure = self._symbol_exposure.get(action.symbol, 0.0)
        headroom = self._config.MAX_SYMBOL_EXPOSURE - current_exposure

        if headroom <= 0:
            return RiskDecision(
                approved=False,
                sized_quantity=None,
                rejection_reason="EXCEEDS_SYMBOL_EXPOSURE",
            )

        sized_quantity = min(action.raw_quantity, headroom)
        self._symbol_exposure[action.symbol] = current_exposure + sized_quantity

        return RiskDecision(
            approved=True,
            sized_quantity=sized_quantity,
            rejection_reason=None,
        )
