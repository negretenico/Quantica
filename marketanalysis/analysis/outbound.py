import json
import logging
import redis
from app.config import Config

logger = logging.getLogger(__name__)

_redis = redis.Redis(host=Config.REDIS_HOST, port=6379, db=0, decode_responses=True)


def send_msg(prediction):
    if not prediction or not isinstance(prediction, tuple) or len(prediction) != 3:
        logger.warning(f"Invalid prediction received: {prediction}")
        return
    event, label, anomaly_score = prediction
    event["cluster_id"] = int(label)
    event["anomaly_score"] = float(anomaly_score)

    symbol = event.get("symbol", "unknown")
    event_time = event.get("eventTime", "unknown")
    key = f"enrichment:{symbol}:{event_time}"

    _redis.setex(key, Config.REDIS_ENRICHMENT_TTL, json.dumps(event))
    logger.debug(f"Wrote enrichment to Redis key '{key}'")