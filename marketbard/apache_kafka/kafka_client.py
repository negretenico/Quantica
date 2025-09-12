import logging
from typing import Any

from app.config import Config
from apache_kafka.consumer import Consumer

logger = logging.getLogger(__name__)


class KafkaClientManager:
    def __init__(self, config: Config):
        self.consumer = Consumer(
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            offset=config.KAFKA_AUTO_OFFSET_RESET,
            group=config.KAFKA_CONSUMER_GROUP,
        )

    def subscribe(self, topic: str, handler):
        self.consumer.register_handler(topic, handler)

    def start_consuming(self):
        self.consumer.start_consuming()

    def stop_consuming(self):
        self.consumer.stop_consuming()
