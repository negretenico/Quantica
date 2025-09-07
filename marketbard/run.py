from app.kafka_client_manager import KafkaClientManager
from app.config import Config
from app.redis_client import RedisClient
import logging

logger = logging.getLogger(__name__)

redis_client = RedisClient(host=Config.REDIS_HOST)

def kafka_event_handler(event, key):
    """Handler called by Kafka consumer for each new event"""
    logger.info(f"Received event from Kafka: {event}")
    # Push event into Redis buffer
    # (later this will trigger batching logic)
    redis_client.add_to_buffer(event)

def main():
    kafka_manager = KafkaClientManager(config=Config)
    kafka_manager.subscribe(
        topic=Config.KAFKA_INPUT_TOPIC,
        handler=kafka_event_handler
    )
    kafka_manager.start_consuming()
