from __future__ import annotations

import logging

from app.metrics import risk_rejections_total
from trade.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


class RiskGateStep:
    def __init__(self):
        self._rejection_logged: set[tuple[str, str]] = set()

    def execute(self, ctx: PipelineContext) -> bool:
        if not ctx.risk_decision.approved:
            risk_rejections_total.labels(
                symbol=ctx.decision["symbol"],
                reason=ctx.risk_decision.rejection_reason,
            ).inc()
            key = (ctx.decision["symbol"], ctx.risk_decision.rejection_reason)
            if key not in self._rejection_logged:
                logger.warning(
                    "Risk REJECTED — symbol=%s action=%s reason=%s (further duplicates suppressed)",
                    ctx.decision["symbol"],
                    ctx.decision["action"],
                    ctx.risk_decision.rejection_reason,
                )
                self._rejection_logged.add(key)
            return False

        ctx.decision["risk_approved"] = True
        ctx.decision["sized_quantity"] = ctx.risk_decision.sized_quantity

        return True
