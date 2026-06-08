import logging
from app.config import Config
from rabbitmq.publisher import RabbitPublisher

logger = logging.getLogger(__name__)

_publisher = RabbitPublisher(url=Config.RABBITMQ_URL, exchange=Config.ANALYTICS_EXCHANGE)


def send_msg(prediction):
    if not prediction or not isinstance(prediction, tuple) or len(prediction) != 3:
        logger.warning(f"Invalid prediction received: {prediction}")
        return
    event, label, anomaly_score = prediction
    event["cluster_id"] = int(label)
    event["anomaly_score"] = float(anomaly_score)

    symbol = event.get("symbol", "unknown")
    _publisher.publish(routing_key=f"signal.analytics.{symbol}", payload=event)
    logger.debug(f"Published enriched event for symbol='{symbol}'")
