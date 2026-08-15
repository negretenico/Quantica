from __future__ import annotations

import logging

from app.config import Config
from app.metrics import decisions_total, rate_limited_total, rate_limiter_utilization
from trade.decision import decide as make_decision
from trade.pipeline.context import PipelineContext
from trade.rate_limiter import TradeRateLimiter

logger = logging.getLogger(__name__)


class DecideStep:
    def __init__(self, config: Config, rate_limiter: TradeRateLimiter | None = None):
        self._config = config
        self._rate_limiter = rate_limiter
        self._rate_limited_logged: set[str] = set()

    def execute(self, ctx: PipelineContext) -> bool:
        decision = make_decision(ctx.event, self._config)
        ctx.decision = decision
        decisions_total.labels(
            symbol=decision["symbol"], action=decision["action"],
        ).inc()

        if decision["action"] == "HOLD":
            logger.debug("HOLD — skipping risk evaluation for %s", decision["symbol"])
            return False

        if self._rate_limiter is not None:
            allowed, reason = self._rate_limiter.check(decision["symbol"])
            rate_limiter_utilization.labels(symbol=decision["symbol"]).set(
                len(self._rate_limiter._windows.get(decision["symbol"], [])) / self._rate_limiter._max
            )
            if not allowed:
                rate_limited_total.labels(symbol=decision["symbol"]).inc()
                if decision["symbol"] not in self._rate_limited_logged:
                    logger.warning(
                        "Rate LIMITED — symbol=%s %s (further suppressed)",
                        decision["symbol"],
                        reason,
                    )
                    self._rate_limited_logged.add(decision["symbol"])
                return False

        return True
