from __future__ import annotations

import logging
from typing import Callable

from app.config import Config
from app.metrics import observe_risk_evaluation
from marketrisk.risk.engine import RiskEngine
from marketrisk.risk.models import ProposedAction
from trade.pipeline.context import PipelineContext
from trade.portfolio import Portfolio

logger = logging.getLogger(__name__)


class RiskEvaluateStep:
    def __init__(
        self,
        risk_engine: RiskEngine,
        config: Config,
        portfolio: Portfolio | None = None,
        price_fn: Callable[[str], float] | None = None,
    ):
        self._risk_engine = risk_engine
        self._config = config
        self._portfolio = portfolio
        self._price_fn = price_fn

    def execute(self, ctx: PipelineContext) -> bool:
        portfolio_value = 0.0
        portfolio_pnl = 0.0
        if self._portfolio is not None and self._price_fn is not None:
            portfolio_value = self._portfolio.total_value(self._price_fn)
            portfolio_pnl = self._portfolio.portfolio_pnl(self._price_fn)

        proposed = ProposedAction(
            symbol=ctx.decision["symbol"],
            action=ctx.decision["action"],
            entry_price=ctx.decision["entry_price"],
            raw_quantity=ctx.decision["raw_quantity"],
            portfolio_value=portfolio_value,
        )

        ctx.risk_decision = self._risk_engine.evaluate(proposed, portfolio_pnl=portfolio_pnl)
        observe_risk_evaluation(
            ctx.risk_decision,
            ctx.decision["symbol"],
            self._risk_engine,
            self._config.risk.MAX_SYMBOL_EXPOSURE,
        )

        return True
