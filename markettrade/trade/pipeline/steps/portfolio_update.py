from __future__ import annotations

import logging
from typing import Callable

from trade.pipeline.context import PipelineContext
from trade.portfolio import Portfolio, PositionTimeoutScheduler

logger = logging.getLogger(__name__)


class PortfolioUpdateStep:
    def __init__(
        self,
        portfolio: Portfolio,
        timeout_scheduler: PositionTimeoutScheduler,
        price_fn: Callable[[str], float],
        state_path: str,
    ):
        self._portfolio = portfolio
        self._timeout_scheduler = timeout_scheduler
        self._price_fn = price_fn
        self._state_path = state_path

    def execute(self, ctx: PipelineContext) -> bool:
        from app.metrics import portfolio_value, positions_open, trades_executed, realized_pnl_total

        action = ctx.decision["action"]
        symbol = ctx.decision["symbol"]
        entry_price = ctx.decision["entry_price"]
        sized_quantity = ctx.decision["sized_quantity"]

        if action == "BUY":
            self._portfolio.record_buy(symbol, entry_price, sized_quantity)
            self._timeout_scheduler.schedule(symbol)
        elif action == "SELL":
            if self._portfolio.has_position(symbol):
                self._portfolio.close_position(symbol, entry_price)
                self._timeout_scheduler.cancel(symbol)

        portfolio_value.set(self._portfolio.total_value(self._price_fn))
        positions_open.set(len(self._portfolio.positions))
        trades_executed.labels(action=action).inc()
        realized_pnl_total.set(self._portfolio.realized_pnl)

        self._portfolio.save(self._state_path)
        return True
