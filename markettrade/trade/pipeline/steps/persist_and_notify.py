from __future__ import annotations

import logging
from datetime import datetime, timezone

from shared.rabbitmq.publisher import RabbitPublisher
from trade.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


class PersistAndNotifyStep:
    def __init__(self, store, notify_publisher: RabbitPublisher):
        self._store = store
        self._notify_publisher = notify_publisher

    def execute(self, ctx: PipelineContext) -> bool:
        try:
            self._store.write(ctx.decision)
            try:
                self._notify_publisher.publish("publish.markettrade", {
                    "type": "publish_success",
                    "source": "markettrade",
                    "symbol": ctx.decision["symbol"],
                    "action": ctx.decision["action"],
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                })
            except Exception:
                logger.debug("Failed to publish notification event")
        except Exception as e:
            try:
                self._notify_publisher.publish("publish.markettrade", {
                    "type": "publish_failure",
                    "source": "markettrade",
                    "error": str(e),
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                })
            except Exception:
                logger.debug("Failed to publish failure notification event")
            raise

        return True
