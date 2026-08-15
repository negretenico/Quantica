import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class RabbitMQConfig:
    URL: str = os.environ.get('RABBITMQ_URL', 'amqp://guest:guest@localhost/')
    QUEUE: str = os.environ.get('RABBITMQ_QUEUE', 'analytics.trade')
    EXCHANGE: str = os.environ.get('TRADE_EXCHANGE', 'analytics')
    EXCHANGE_TYPE: str = os.environ.get('TRADE_EXCHANGE_TYPE', 'topic')
    ROUTING_KEY: str = os.environ.get('TRADE_ROUTING_KEY', 'signal.analytics.#')
    MAX_RETRIES: int = int(os.environ.get('RABBITMQ_MAX_RETRIES', '3'))
    RETRY_BASE_DELAY: float = float(os.environ.get('RABBITMQ_RETRY_BASE_DELAY', '1.0'))


@dataclass
class BlobStoreConfig:
    PATH: str = os.environ.get('BLOB_STORE_PATH', './decisions')
    BACKEND: str = os.environ.get('BLOB_STORE_BACKEND', 'disk')


@dataclass
class RiskConfig:
    MAX_TRADE_QUANTITY: float = float(os.environ.get('MAX_TRADE_QUANTITY', '1000.0'))
    MAX_SYMBOL_EXPOSURE: float = float(os.environ.get('MAX_SYMBOL_EXPOSURE', '5000.0'))
    MAX_DRAWDOWN_PCT: float = float(os.environ.get('MAX_DRAWDOWN_PCT', '0.20'))
    NEAR_LIMIT_THRESHOLD_PCT: float = float(os.environ.get('NEAR_LIMIT_THRESHOLD_PCT', '0.80'))
    CONCENTRATION_THRESHOLD: int = int(os.environ.get('CONCENTRATION_THRESHOLD', '3'))


@dataclass
class LookbackConfig:
    ENABLED: bool = os.environ.get('LOOKBACK_ENABLED', 'true').lower() == 'true'
    WINDOWS: list[int] = None
    BINANCE_BASE_URL: str = os.environ.get('BINANCE_BASE_URL', 'https://api.binance.com')
    BINANCE_TIMEOUT: int = int(os.environ.get('BINANCE_TIMEOUT', '5'))
    MAX_PENDING: int = int(os.environ.get('LOOKBACK_MAX_PENDING', '5000'))
    STORE_PATH: str = os.environ.get('LOOKBACK_STORE_PATH', './decisions/lookback')

    def __post_init__(self):
        if self.WINDOWS is None:
            raw = os.environ.get('LOOKBACK_WINDOWS', '60,300,900')
            self.WINDOWS = [int(w.strip()) for w in raw.split(',')]


@dataclass
class PriceSanityConfig:
    ENABLED: bool = os.environ.get('PRICE_SANITY_ENABLED', 'true').lower() == 'true'
    MIN_PRICE: float = float(os.environ.get('PRICE_SANITY_MIN', '0.0001'))
    MAX_PRICE: float = float(os.environ.get('PRICE_SANITY_MAX', '10000000.0'))


@dataclass
class RateLimiterConfig:
    ENABLED: bool = os.environ.get('RATE_LIMITER_ENABLED', 'true').lower() == 'true'
    MAX_PER_MINUTE: int = int(os.environ.get('RATE_LIMITER_MAX_PER_MINUTE', '10'))
    WINDOW_SECONDS: float = float(os.environ.get('RATE_LIMITER_WINDOW_SECONDS', '60.0'))


@dataclass
class CalibrationConfig:
    WINDOW_SIZE: int = int(os.environ.get('CALIBRATION_WINDOW_SIZE', '200'))
    DRIFT_THRESHOLD: float = float(os.environ.get('CALIBRATION_DRIFT_THRESHOLD', '0.40'))
    OVERFIT_THRESHOLD: float = float(os.environ.get('CALIBRATION_OVERFIT_THRESHOLD', '0.85'))
    MIN_SAMPLES: int = int(os.environ.get('CALIBRATION_MIN_SAMPLES', '20'))


@dataclass
class Config:
    rabbitmq: RabbitMQConfig = None
    blob_store: BlobStoreConfig = None
    risk: RiskConfig = None
    lookback: LookbackConfig = None
    price_sanity: PriceSanityConfig = None
    rate_limiter: RateLimiterConfig = None
    calibration: CalibrationConfig = None
    ANOMALY_SCORE_THRESHOLD: float = float(os.environ.get('ANOMALY_SCORE_THRESHOLD', '0.7'))
    DECISION_LOG_MAX_SIZE: int = int(os.environ.get('DECISION_LOG_MAX_SIZE', '1000'))
    OUTCOME_STORE_PATH: str = os.environ.get('OUTCOME_STORE_PATH', './decisions/outcomes')
    OUTCOME_FLUSH_COUNT: int = int(os.environ.get('OUTCOME_FLUSH_COUNT', '10'))
    OUTCOME_FLUSH_INTERVAL: float = float(os.environ.get('OUTCOME_FLUSH_INTERVAL', '60.0'))
    RISK_ALERT_STORE_PATH: str = os.environ.get('RISK_ALERT_STORE_PATH', './decisions/risk-alerts')

    def __post_init__(self):
        if self.rabbitmq is None:
            self.rabbitmq = RabbitMQConfig()
        if self.blob_store is None:
            self.blob_store = BlobStoreConfig()
        if self.risk is None:
            self.risk = RiskConfig()
        if self.lookback is None:
            self.lookback = LookbackConfig()
        if self.price_sanity is None:
            self.price_sanity = PriceSanityConfig()
        if self.rate_limiter is None:
            self.rate_limiter = RateLimiterConfig()
        if self.calibration is None:
            self.calibration = CalibrationConfig()

    def __str__(self):
        return (
            f"RabbitMQ: {self.rabbitmq.URL}\n"
            f"Queue: {self.rabbitmq.QUEUE}\n"
            f"Signal Exchange: {self.rabbitmq.SIGNAL_EXCHANGE}\n"
            f"Blob Store Path: {self.blob_store.PATH}\n"
            f"Blob Store Backend: {self.blob_store.BACKEND}"
        )
