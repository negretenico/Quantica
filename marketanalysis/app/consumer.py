import json
import threading
from typing import Callable, Dict

from kafka import KafkaConsumer
from kafka.errors import KafkaError
import logging
logger = logging.getLogger(__name__)


class Consumer:
    def __init__(self, group, offset, bootstrap_servers):
        self.running = False
        self.message_handlers: Dict[str, Callable] = {}
        self.consumer_thread = None
        """Initialize Kafka consumer"""
        try:
            self.consumer = KafkaConsumer(
                bootstrap_servers=bootstrap_servers,
                group_id=group,
                auto_offset_reset=offset,
                enable_auto_commit=True,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')) if x else None,
                key_deserializer=lambda x: x.decode('utf-8') if x else None,
            )
            logger.info("Kafka consumer initialized successfully")
        except KafkaError as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}")

    def register_handler(self, topic: str, handler: Callable):
        """Register message handler for a topic"""
        self.message_handlers[topic] = handler
        if self.consumer:
            self.consumer.subscribe([topic])

    def start_consuming(self):
        """Start consuming messages in a separate thread"""
        if self.running:
            return

        self.running = True
        self.consumer_thread = threading.Thread(target=self._consume_messages, daemon=True)
        self.consumer_thread.start()
        logger.info(f"Started Kafka consumer thread {self.consumer_thread.getName()}")

    def stop_consuming(self):
        """Stop consuming messages"""
        self.running.clear()
        self.consumer.wakeup()   # immediately interrupts poll()
        self.consumer_thread.join()
        logger.info("Stopped Kafka consumer")

    def _consume_messages(self):
        """Internal method to consume messages"""
        if not self.consumer:
            logger.error("Consumer not initialized")
            return

        try:
            for message in self.consumer:
                if not self.running:
                    break

                topic = message.topic
                if topic in self.message_handlers:
                    try:
                        self.message_handlers[topic](message.value, message.key)
                    except Exception as e:
                        logger.error(f"Error processing message from {topic}: {e}")
                else:
                    logger.warning(f"No handler registered for topic: {topic}")

        except Exception as e:
            logger.error(f"Consumer error: {e}")
