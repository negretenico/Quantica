import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


@dataclass
class Config:
    MARKETSERVER_BASE_URL: str = field(default_factory=lambda: _env("MARKETSERVER_BASE_URL", "http://localhost:5001"))
    METRICS_PORT: int = field(default_factory=lambda: int(_env("METRICS_PORT", "8000")))
    LOG_LEVEL: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))
    RISK_MAX_SYMBOL_EXPOSURE: float = field(default_factory=lambda: float(_env("RISK_MAX_SYMBOL_EXPOSURE", "1.0")))
    TRADE_HISTORY_DAYS_DEFAULT: int = field(default_factory=lambda: int(_env("TRADE_HISTORY_DAYS_DEFAULT", "7")))
    MAX_QUERY_DAYS: int = field(default_factory=lambda: int(_env("MAX_QUERY_DAYS", "30")))
    RESOURCE_CACHE_TTL_SECONDS: int = field(default_factory=lambda: int(_env("RESOURCE_CACHE_TTL_SECONDS", "15")))

    def __str__(self):
        return (
            f"MarketServer: {self.MARKETSERVER_BASE_URL}\n"
            f"Metrics Port: {self.METRICS_PORT}\n"
            f"Log Level: {self.LOG_LEVEL}\n"
            f"Risk Max Symbol Exposure: {self.RISK_MAX_SYMBOL_EXPOSURE}\n"
            f"Trade History Days Default: {self.TRADE_HISTORY_DAYS_DEFAULT}\n"
            f"Max Query Days: {self.MAX_QUERY_DAYS}\n"
            f"Resource Cache TTL: {self.RESOURCE_CACHE_TTL_SECONDS}s"
        )
