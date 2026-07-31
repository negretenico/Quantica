import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class RabbitMQConfig:
    URL: str = os.environ.get('RABBITMQ_URL', 'amqp://guest:guest@localhost/')
    QUEUE: str = os.environ.get('RABBITMQ_QUEUE', 'signal.trade')
    SIGNAL_EXCHANGE: str = os.environ.get('SIGNAL_EXCHANGE', 'signal')


@dataclass
class BlobStoreConfig:
    PATH: str = os.environ.get('BLOB_STORE_PATH', './decisions')
    BACKEND: str = os.environ.get('BLOB_STORE_BACKEND', 'disk')


@dataclass
class RiskConfig:
    MAX_TRADE_QUANTITY: float = float(os.environ.get('MAX_TRADE_QUANTITY', '1000.0'))
    MAX_SYMBOL_EXPOSURE: float = float(os.environ.get('MAX_SYMBOL_EXPOSURE', '5000.0'))
    MAX_DRAWDOWN_PCT: float = float(os.environ.get('MAX_DRAWDOWN_PCT', '0.20'))


@dataclass
class Config:
    rabbitmq: RabbitMQConfig = None
    blob_store: BlobStoreConfig = None
    risk: RiskConfig = None
    ANOMALY_SCORE_THRESHOLD: float = float(os.environ.get('ANOMALY_SCORE_THRESHOLD', '0.7'))

    def __post_init__(self):
        if self.rabbitmq is None:
            self.rabbitmq = RabbitMQConfig()
        if self.blob_store is None:
            self.blob_store = BlobStoreConfig()
        if self.risk is None:
            self.risk = RiskConfig()

    def __str__(self):
        return (
            f"RabbitMQ: {self.rabbitmq.URL}\n"
            f"Queue: {self.rabbitmq.QUEUE}\n"
            f"Signal Exchange: {self.rabbitmq.SIGNAL_EXCHANGE}\n"
            f"Blob Store Path: {self.blob_store.PATH}\n"
            f"Blob Store Backend: {self.blob_store.BACKEND}"
        )
