from __future__ import annotations

import logging
from typing import Protocol

from trade.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


class Step(Protocol):
    def execute(self, ctx: PipelineContext) -> bool: ...


class Pipeline:
    def __init__(self, steps: list[Step]):
        self._steps = steps

    def execute(self, ctx: PipelineContext) -> None:
        for step in self._steps:
            if not step.execute(ctx):
                return
