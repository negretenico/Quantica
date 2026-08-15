from __future__ import annotations

import logging

from app.config import Config
from app.metrics import (
    accumulation_alerts_total,
    concentration_active,
    concentration_alerts_total,
    near_limit_active_symbols,
    near_limit_alerts_total,
    near_limit_ratio,
)
from marketrisk.risk.models import (
    AccumulationAlert,
    AccumulationCleared,
    ConcentrationAlert,
    ConcentrationCleared,
    NearLimitAlert,
    NearLimitCleared,
)
from marketrisk.risk.observer import NearLimitObserver, RiskObserverPipeline
from trade.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


class NearLimitStep:
    def __init__(
        self,
        risk_observer_pipeline: RiskObserverPipeline,
        near_limit_observer: NearLimitObserver,
        risk_alert_store,
        config: Config,
        risk_engine,
    ):
        self._risk_observer_pipeline = risk_observer_pipeline
        self._near_limit_observer = near_limit_observer
        self._risk_alert_store = risk_alert_store
        self._config = config
        self._risk_engine = risk_engine
        self._near_limit_logged: set[str] = set()
        self._accumulation_logged: set[str] = set()

    def execute(self, ctx: PipelineContext) -> bool:
        risk_results = self._risk_observer_pipeline.check(
            symbol=ctx.decision["symbol"],
            current_exposure=self._risk_engine.get_symbol_exposure(ctx.decision["symbol"]),
            max_exposure=self._config.risk.MAX_SYMBOL_EXPOSURE,
            action=ctx.decision["action"],
            approved=ctx.risk_decision.approved,
        )
        for result in risk_results:
            match result:
                case NearLimitAlert() as alert:
                    self._risk_alert_store.write(alert.to_dict())
                    near_limit_alerts_total.labels(symbol=alert.symbol).inc()
                    near_limit_ratio.labels(symbol=alert.symbol).set(alert.ratio)
                    if alert.symbol not in self._near_limit_logged:
                        logger.warning(
                            "NEAR-LIMIT exposure — symbol=%s ratio=%.2f (%.0f/%.0f) "
                            "(further alerts suppressed until cleared)",
                            alert.symbol, alert.ratio, alert.current_exposure, alert.max_exposure,
                        )
                        self._near_limit_logged.add(alert.symbol)
                case NearLimitCleared() as cleared:
                    self._near_limit_logged.discard(cleared.symbol)
                case ConcentrationAlert() as alert:
                    self._risk_alert_store.write(alert.to_dict())
                    concentration_alerts_total.inc()
                    concentration_active.set(1)
                case ConcentrationCleared():
                    concentration_active.set(0)
                case AccumulationAlert() as alert:
                    self._risk_alert_store.write(alert.to_dict())
                    accumulation_alerts_total.labels(
                        symbol=alert.symbol, direction=alert.direction,
                    ).inc()
                    if alert.symbol not in self._accumulation_logged:
                        logger.warning(
                            "ACCUMULATION alert — symbol=%s direction=%s count=%d "
                            "(further alerts suppressed until direction change)",
                            alert.symbol, alert.direction, alert.consecutive_count,
                        )
                        self._accumulation_logged.add(alert.symbol)
                case AccumulationCleared() as cleared:
                    self._accumulation_logged.discard(cleared.symbol)
        near_limit_active_symbols.set(len(self._near_limit_observer.active_symbols()))

        return True
