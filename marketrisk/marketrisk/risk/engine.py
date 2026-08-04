from __future__ import annotations

from marketrisk.app.config import Config
from marketrisk.risk.models import ProposedAction, RiskDecision


class RiskEngine:
    """Evaluates proposed actions against per-trade and per-symbol risk caps.

    Note: _symbol_exposure is not thread-safe. This engine is intended for
    single-threaded use within the markettrade worker process.
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._symbol_exposure: dict[str, float] = {}
        self._peak_pnl: float = 0.0

    def _drawdown(self, portfolio_pnl: float) -> float:
        if self._peak_pnl == 0:
            return 0.0
        return (self._peak_pnl - portfolio_pnl) / abs(self._peak_pnl)

    def evaluate(self, action: ProposedAction, portfolio_pnl: float = 0.0) -> RiskDecision:
        self._peak_pnl = max(self._peak_pnl, portfolio_pnl)

        if self._drawdown(portfolio_pnl) > self._config.MAX_DRAWDOWN_PCT:
            return RiskDecision(
                approved=False,
                sized_quantity=None,
                rejection_reason="PORTFOLIO_DRAWDOWN_HALT",
            )

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

    def get_symbol_exposure(self, symbol: str) -> float:
        return self._symbol_exposure.get(symbol, 0.0)
