import logging
from typing import Any

from app.config import Config
from app.consumer import Consumer
from app.producer import Producer

logger = logging.getLogger(__name__)


class KafkaClientManager:
    def __init__(self, config: Config):
        print(f"This is the config {config}")
        self.producer = Producer(bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS)
        self.consumer = Consumer(bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
                                 offset=config.KAFKA_AUTO_OFFSET_RESET, group=config.KAFKA_CONSUMER_GROUP)

    def subscribe(self, topic: str, handler):
        self.consumer.register_handler(topic, handler)

    def start_consuming(self):
        self.consumer.start_consuming()

    def stop_consuming(self):
        self.consumer.stop_consuming()

    def publish(self, topic: str, message: Any):
        self.producer.send_message(topic=topic, message=message)
