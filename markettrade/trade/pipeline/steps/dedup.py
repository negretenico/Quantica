from __future__ import annotations

import logging

from app.metrics import duplicates_dropped_total, events_received_total
from shared.dedup import DedupFilter
from trade.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


class DedupStep:
    def __init__(self, dedup: DedupFilter):
        self._dedup = dedup

    def execute(self, ctx: PipelineContext) -> bool:
        events_received_total.inc()

        if self._dedup.is_duplicate(ctx.payload):
            duplicates_dropped_total.inc()
            logger.debug("Duplicate event dropped: %s", ctx.payload.get("symbol"))
            return False

        return True
