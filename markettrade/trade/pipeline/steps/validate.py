from __future__ import annotations

import logging
import time

from app.metrics import (
    observe_tick_to_trade,
    validation_errors_total,
    validation_pipeline_rejections_total,
    validation_pipeline_seconds,
)
from trade.pipeline.context import PipelineContext
from trade.validation import ValidationPipeline

logger = logging.getLogger(__name__)


class ValidateStep:
    def __init__(self, validation_pipeline: ValidationPipeline, price_cache=None):
        self._validation_pipeline = validation_pipeline
        self._price_cache = price_cache
        self._rejection_logged: set[tuple[str, str]] = set()

    def execute(self, ctx: PipelineContext) -> bool:
        with validation_pipeline_seconds.time():
            vresult = self._validation_pipeline.run(ctx.payload)

        if not vresult.valid:
            stage = "schema" if vresult.reason != "price_out_of_range" else "price_sanity"
            validation_pipeline_rejections_total.labels(
                stage=stage, reason=vresult.reason,
            ).inc()
            validation_errors_total.labels(reason=vresult.reason).inc()
            symbol = ctx.payload.get("symbol", "unknown")
            key = (stage, str(symbol))
            if key not in self._rejection_logged:
                logger.warning(
                    "Validation REJECTED — stage=%s symbol=%s reason=%s (further duplicates suppressed)",
                    stage,
                    symbol,
                    vresult.reason,
                )
                self._rejection_logged.add(key)
            return False

        ctx.event = vresult.event

        logger.debug(
            "Received signal — symbol=%s type=%s",
            ctx.event.symbol,
            ctx.event.type,
        )

        observe_tick_to_trade(ctx.payload)

        if self._price_cache is not None:
            ts = ctx.event.eventTime / 1000.0 if ctx.event.eventTime else time.time()
            self._price_cache.record(ctx.event.symbol, ts, ctx.event.price)

        return True
