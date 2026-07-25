import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    RABBITMQ_URL = os.environ.get('RABBITMQ_URL', 'amqp://guest:guest@localhost/')
    RABBITMQ_QUEUE = os.environ.get('RABBITMQ_QUEUE', 'signal.trade')
    ANALYTICS_EXCHANGE = os.environ.get('ANALYTICS_EXCHANGE', 'analytics')
    BLOB_STORE_PATH = os.environ.get('BLOB_STORE_PATH', './decisions')
    BLOB_STORE_BACKEND = os.environ.get('BLOB_STORE_BACKEND', 'disk')

    def __str__(self):
        return (
            f"RabbitMQ: {self.RABBITMQ_URL}\n"
            f"Queue: {self.RABBITMQ_QUEUE}\n"
            f"Analytics Exchange: {self.ANALYTICS_EXCHANGE}\n"
            f"Blob Store Path: {self.BLOB_STORE_PATH}\n"
            f"Blob Store Backend: {self.BLOB_STORE_BACKEND}"
        )
