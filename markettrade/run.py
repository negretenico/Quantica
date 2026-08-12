import logging
import time
import threading
from datetime import datetime, timezone

from pydantic import ValidationError

from app.config import Config
from app.metrics import (
    accumulation_alerts_total,
    concentration_active,
    concentration_alerts_total,
    decisions_total,
    duplicates_dropped_total,
    events_received_total,
    near_limit_active_symbols,
    near_limit_alerts_total,
    near_limit_ratio,
    observe_risk_evaluation,
    observe_tick_to_trade,
    outcome_record_errors_total,
    outcome_records_total,
    rate_limited_total,
    rate_limiter_utilization,
    risk_rejections_total,
    start_metrics_server,
    validation_errors_total,
)
from app.rabbit_client import SignalRabbitClient
from marketrisk.risk.engine import RiskEngine
from marketrisk.risk.models import (
    AccumulationAlert,
    AccumulationCleared,
    ConcentrationAlert,
    ConcentrationCleared,
    NearLimitAlert,
    NearLimitCleared,
    ProposedAction,
)
from marketrisk.risk.observer import (
    AccumulationObserver,
    ConcentrationObserver,
    NearLimitObserver,
    RiskObserverPipeline,
)
from shared.blob import get_store
from shared.dedup import DedupFilter
from shared.rabbitmq.publisher import RabbitPublisher
from trade.decision import decide
from trade.models import SignalEvent
from trade.outcome import DecisionLog
from trade.calibration import CalibrationEngine
from trade.outcome_tracker import OutcomeTracker
from trade.price_lookback import create_lookback
from trade.rate_limiter import TradeRateLimiter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    config = Config()
    client = SignalRabbitClient(config.rabbitmq)
    risk_engine = RiskEngine(config.risk)
    near_limit_observer = NearLimitObserver(threshold_pct=config.risk.NEAR_LIMIT_THRESHOLD_PCT)
    concentration_observer = ConcentrationObserver(
        near_limit_observer, max_correlated=config.risk.CONCENTRATION_THRESHOLD,
    )
    accumulation_observer = AccumulationObserver(
        threshold=config.risk.ACCUMULATION_THRESHOLD,
    )
    risk_observer_pipeline = RiskObserverPipeline([
        near_limit_observer, concentration_observer, accumulation_observer,
    ])
    store = get_store(config.blob_store.BACKEND, config.blob_store.PATH)
    outcome_store = get_store(config.blob_store.BACKEND, config.OUTCOME_STORE_PATH)
    risk_alert_store = get_store(config.blob_store.BACKEND, config.RISK_ALERT_STORE_PATH)
    decision_log = DecisionLog(outcome_store, max_size=config.DECISION_LOG_MAX_SIZE)
    outcome_tracker = OutcomeTracker()
    calibration_engine = CalibrationEngine(window_size=config.calibration.WINDOW_SIZE)
    outcome_tracker.add_on_outcome(calibration_engine.record)
    dedup = DedupFilter()

    notify_publisher = RabbitPublisher(
        url=config.rabbitmq.URL,
        exchange="notifications",
    )
    lookback, price_cache = create_lookback(config, outcome_tracker=outcome_tracker)

    rate_limiter = None
    if config.rate_limiter.ENABLED:
        rate_limiter = TradeRateLimiter(
            max_per_minute=config.rate_limiter.MAX_PER_MINUTE,
            window_seconds=config.rate_limiter.WINDOW_SECONDS,
        )
        logger.info(
            "Rate limiter enabled — max %d per symbol per %.0fs",
            config.rate_limiter.MAX_PER_MINUTE,
            config.rate_limiter.WINDOW_SECONDS,
        )

    start_metrics_server()
    logger.info("Prometheus metrics server started on :8000")

    _rejected_logged: set[tuple[str, str]] = set()
    _validation_logged: set[tuple[str, str]] = set()
    _near_limit_logged: set[str] = set()
    _accumulation_logged: set[str] = set()
    _rate_limited_logged: set[str] = set()

    def handle_message(payload):
        events_received_total.inc()

        if dedup.is_duplicate(payload):
            duplicates_dropped_total.inc()
            logger.debug("Duplicate event dropped: %s", payload.get("symbol"))
            return

        try:
            event = SignalEvent(**payload)
        except ValidationError as e:
            reason = e.errors()[0]["loc"][0] if e.errors() else "unknown"
            validation_errors_total.labels(reason=reason).inc()
            symbol = payload.get("symbol", "unknown")
            key = (str(symbol), str(reason))
            if key not in _validation_logged:
                logger.warning(
                    "Validation REJECTED — symbol=%s reason=%s (further duplicates suppressed)",
                    symbol,
                    reason,
                )
                _validation_logged.add(key)
            return

        logger.debug(
            "Received signal — symbol=%s type=%s",
            event.symbol,
            event.type,
        )

        observe_tick_to_trade(payload)

        if price_cache is not None:
            ts = event.eventTime / 1000.0 if event.eventTime else time.time()
            price_cache.record(event.symbol, ts, event.price)

        decision = decide(event, config)
        decisions_total.labels(
            symbol=decision["symbol"], action=decision["action"]
        ).inc()

        if decision["action"] == "HOLD":
            logger.debug("HOLD — skipping risk evaluation for %s", decision["symbol"])
            return

        if rate_limiter is not None:
            allowed, reason = rate_limiter.check(decision["symbol"])
            rate_limiter_utilization.labels(symbol=decision["symbol"]).set(
                len(rate_limiter._windows.get(decision["symbol"], [])) / rate_limiter._max
            )
            if not allowed:
                rate_limited_total.labels(symbol=decision["symbol"]).inc()
                if decision["symbol"] not in _rate_limited_logged:
                    logger.warning(
                        "Rate LIMITED — symbol=%s %s (further suppressed)",
                        decision["symbol"],
                        reason,
                    )
                    _rate_limited_logged.add(decision["symbol"])
                return

        proposed = ProposedAction(
            symbol=decision["symbol"],
            action=decision["action"],
            entry_price=decision["entry_price"],
            raw_quantity=decision["raw_quantity"],
            portfolio_value=0.0,
        )

        risk_decision = risk_engine.evaluate(proposed)
        observe_risk_evaluation(risk_decision, decision["symbol"], risk_engine, config.risk.MAX_SYMBOL_EXPOSURE)

        risk_results = risk_observer_pipeline.check(
            symbol=decision["symbol"],
            current_exposure=risk_engine.get_symbol_exposure(decision["symbol"]),
            max_exposure=config.risk.MAX_SYMBOL_EXPOSURE,
            action=decision["action"],
            approved=risk_decision.approved,
        )
        for result in risk_results:
            match result:
                case NearLimitAlert() as alert:
                    risk_alert_store.write(alert.to_dict())
                    near_limit_alerts_total.labels(symbol=alert.symbol).inc()
                    near_limit_ratio.labels(symbol=alert.symbol).set(alert.ratio)
                    if alert.symbol not in _near_limit_logged:
                        logger.warning(
                            "NEAR-LIMIT exposure — symbol=%s ratio=%.2f (%.0f/%.0f) "
                            "(further alerts suppressed until cleared)",
                            alert.symbol, alert.ratio, alert.current_exposure, alert.max_exposure,
                        )
                        _near_limit_logged.add(alert.symbol)
                case NearLimitCleared() as cleared:
                    _near_limit_logged.discard(cleared.symbol)
                case ConcentrationAlert() as alert:
                    risk_alert_store.write(alert.to_dict())
                    concentration_alerts_total.inc()
                    concentration_active.set(1)
                case ConcentrationCleared():
                    concentration_active.set(0)
                case AccumulationAlert() as alert:
                    risk_alert_store.write(alert.to_dict())
                    accumulation_alerts_total.labels(
                        symbol=alert.symbol, direction=alert.direction,
                    ).inc()
                    if alert.symbol not in _accumulation_logged:
                        logger.warning(
                            "ACCUMULATION alert — symbol=%s direction=%s count=%d "
                            "(further alerts suppressed until direction change)",
                            alert.symbol, alert.direction, alert.consecutive_count,
                        )
                        _accumulation_logged.add(alert.symbol)
                case AccumulationCleared() as cleared:
                    _accumulation_logged.discard(cleared.symbol)
        near_limit_active_symbols.set(len(near_limit_observer.active_symbols()))

        if not risk_decision.approved:
            risk_rejections_total.labels(
                symbol=decision["symbol"],
                reason=risk_decision.rejection_reason,
            ).inc()
            key = (decision["symbol"], risk_decision.rejection_reason)
            if key not in _rejected_logged:
                logger.warning(
                    "Risk REJECTED — symbol=%s action=%s reason=%s (further duplicates suppressed)",
                    decision["symbol"],
                    decision["action"],
                    risk_decision.rejection_reason,
                )
                _rejected_logged.add(key)
            return

        decision["risk_approved"] = True
        decision["sized_quantity"] = risk_decision.sized_quantity

        try:
            decision_log.record(decision)
            outcome_records_total.labels(
                symbol=decision["symbol"], action=decision["action"]
            ).inc()
        except Exception:
            outcome_record_errors_total.labels(symbol=decision["symbol"]).inc()
            logger.exception("Failed to record outcome for %s", decision["symbol"])

        if lookback is not None:
            lookback.schedule(decision)

        try:
            store.write(decision)
            try:
                notify_publisher.publish("publish.markettrade", {
                    "type": "publish_success",
                    "source": "markettrade",
                    "symbol": decision["symbol"],
                    "action": decision["action"],
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                })
            except Exception:
                logger.debug("Failed to publish notification event")
        except Exception as e:
            try:
                notify_publisher.publish("publish.markettrade", {
                    "type": "publish_failure",
                    "source": "markettrade",
                    "error": str(e),
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                })
            except Exception:
                logger.debug("Failed to publish failure notification event")
            raise

    client.subscribe(handle_message)
    client.start_consuming()
    threading.Event().wait()


if __name__ == "__main__":
    main()
