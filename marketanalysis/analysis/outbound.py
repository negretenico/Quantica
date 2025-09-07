import logging
from app import kafka_manager
from app.config import Config
logger = logging.getLogger(__name__)
def send_msg(prediction):
    if not prediction or not isinstance(prediction, tuple) or len(prediction) != 3:
            logger.warning(f"Invalid prediction received: {prediction}")
            return
    event, label,anomaly_score  = prediction
    event["cluster_id"] = int(label)
    event["anomaly_score"] = float(anomaly_score)
    logger.info(f"Publishing event {event } to topic {Config.KAFKA_OUTPUT_TOPIC}")
    # Publish enriched event to Kafka
    kafka_manager.publish(
        topic=Config.KAFKA_OUTPUT_TOPIC,
        message=event
    )