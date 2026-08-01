import logging
import threading

from app.config import Config
from app.rabbit_client import SignalRabbitClient
from marketrisk.risk.engine import RiskEngine
from marketrisk.risk.models import ProposedAction
from shared.blob import get_store
from shared.dedup import DedupFilter
from trade.decision import decide

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
    dedup = DedupFilter()

    def handle_message(payload):
        if dedup.is_duplicate(payload):
            logger.debug("Duplicate event dropped: %s", payload.get("symbol"))
            return

        logger.debug(
            "Received signal — symbol=%s type=%s",
            payload.get("symbol"),
            payload.get("type"),
        )

        decision = decide(payload, config)

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

        if not risk_decision.approved:
            logger.warning(
                "Risk REJECTED — symbol=%s action=%s reason=%s",
                decision["symbol"],
                decision["action"],
                risk_decision.rejection_reason,
            )
            return

        decision["risk_approved"] = True
        decision["sized_quantity"] = risk_decision.sized_quantity
        store.write(decision)

    client.subscribe(handle_message)
    client.start_consuming()
    threading.Event().wait()


if __name__ == "__main__":
    main()
