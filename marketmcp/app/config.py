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

    def __str__(self):
        return (
            f"MarketServer: {self.MARKETSERVER_BASE_URL}\n"
            f"Metrics Port: {self.METRICS_PORT}\n"
            f"Log Level: {self.LOG_LEVEL}"
        )
