from __future__ import annotations

import logging

from app.config import Config
from app.metrics import observe_risk_evaluation
from marketrisk.risk.engine import RiskEngine
from marketrisk.risk.models import ProposedAction
from trade.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


class RiskEvaluateStep:
    def __init__(self, risk_engine: RiskEngine, config: Config):
        self._risk_engine = risk_engine
        self._config = config

    def execute(self, ctx: PipelineContext) -> bool:
        proposed = ProposedAction(
            symbol=ctx.decision["symbol"],
            action=ctx.decision["action"],
            entry_price=ctx.decision["entry_price"],
            raw_quantity=ctx.decision["raw_quantity"],
            portfolio_value=0.0,
        )

        ctx.risk_decision = self._risk_engine.evaluate(proposed)
        observe_risk_evaluation(
            ctx.risk_decision,
            ctx.decision["symbol"],
            self._risk_engine,
            self._config.risk.MAX_SYMBOL_EXPOSURE,
        )

        return True
