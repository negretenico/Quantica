from kafka import KafkaProducer

import json
import logging
from typing import  Dict, Any, Optional

from kafka import KafkaConsumer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)

class Producer:
    def __init__(self, bootstrap_servers):
        """Initialize Kafka producer"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                key_serializer=lambda x: x.encode('utf-8') if x else None,
                retries=3,
                acks='all'
            )
            logger.info("Kafka producer initialized successfully")
        except KafkaError as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")

    def send_message(self, topic: str, message: Dict[str, Any], key: Optional[str] = None):
        """Send message to Kafka topic"""
        if not self.producer:
            logger.error("Producer not initialized")
            return False

        try:
            self.producer.send(topic, value=message, key=key)
            self.producer.flush()
            logger.info(f"Message sent to topic {topic}: {message}")
            return True
        except KafkaError as e:
            logger.error(f"Failed to send message to {topic}: {e}")
            return False
