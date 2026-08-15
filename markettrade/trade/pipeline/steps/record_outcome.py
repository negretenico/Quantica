from __future__ import annotations

import logging

from app.metrics import outcome_record_errors_total, outcome_records_total
from trade.outcome import DecisionLog
from trade.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


class RecordOutcomeStep:
    def __init__(self, decision_log: DecisionLog, lookback=None):
        self._decision_log = decision_log
        self._lookback = lookback

    def execute(self, ctx: PipelineContext) -> bool:
        try:
            self._decision_log.record(ctx.decision)
            outcome_records_total.labels(
                symbol=ctx.decision["symbol"], action=ctx.decision["action"],
            ).inc()
        except Exception:
            outcome_record_errors_total.labels(symbol=ctx.decision["symbol"]).inc()
            logger.exception("Failed to record outcome for %s", ctx.decision["symbol"])

        if self._lookback is not None:
            self._lookback.schedule(ctx.decision)

        return True
