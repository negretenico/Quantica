import logging
import threading
from datetime import datetime, timezone

from pydantic import ValidationError

from app.config import Config
from app.metrics import (
    decisions_total,
    duplicates_dropped_total,
    events_received_total,
    observe_risk_evaluation,
    observe_tick_to_trade,
    outcome_record_errors_total,
    outcome_records_total,
    risk_rejections_total,
    start_metrics_server,
    validation_errors_total,
)
from app.rabbit_client import SignalRabbitClient
from marketrisk.risk.engine import RiskEngine
from marketrisk.risk.models import ProposedAction
from shared.blob import get_store
from shared.dedup import DedupFilter
from shared.rabbitmq.publisher import RabbitPublisher
from trade.decision import decide
from trade.models import SignalEvent
from trade.outcome import DecisionLog

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    config = Config()
    client = SignalRabbitClient(config.rabbitmq)
    risk_engine = RiskEngine(config.risk)
    store = get_store(config.blob_store.BACKEND, config.blob_store.PATH)
    outcome_store = get_store(config.blob_store.BACKEND, config.OUTCOME_STORE_PATH)
    decision_log = DecisionLog(outcome_store, max_size=config.DECISION_LOG_MAX_SIZE)
    dedup = DedupFilter()

    notify_publisher = RabbitPublisher(
        url=config.rabbitmq.URL,
        exchange="notifications",
    )

    start_metrics_server()
    logger.info("Prometheus metrics server started on :8000")

    _rejected_logged: set[tuple[str, str]] = set()
    _validation_logged: set[tuple[str, str]] = set()

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

        decision = decide(event, config)
        decisions_total.labels(
            symbol=decision["symbol"], action=decision["action"]
        ).inc()

        if decision["action"] == "HOLD":
            logger.debug("HOLD — skipping risk evaluation for %s", decision["symbol"])
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
