import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

@dataclass
class Config:
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    RABBITMQ_URL = os.environ.get('RABBITMQ_URL', 'amqp://guest:guest@localhost/')
    RABBITMQ_QUEUE = os.environ.get('RABBITMQ_QUEUE', 'signal.analysis')
    SIGNAL_EXCHANGE = os.environ.get('SIGNAL_EXCHANGE', 'signal')
    ANALYTICS_EXCHANGE = os.environ.get('ANALYTICS_EXCHANGE', 'analytics')
    WARMUP_SAMPLES = int(os.environ.get('WARMUP_SAMPLES', '100'))
    RETRAIN_BUFFER_SIZE = int(os.environ.get('RETRAIN_BUFFER_SIZE', '500'))
    DEDUP_SET_SIZE = int(os.environ.get('DEDUP_SET_SIZE', '10000'))
    ANOMALY_THRESHOLD = float(os.environ.get('ANOMALY_THRESHOLD', '0.9'))

    def __str__(self):
        return (f"RabbitMQ: {self.RABBITMQ_URL}\n"
                f"Queue: {self.RABBITMQ_QUEUE}")
