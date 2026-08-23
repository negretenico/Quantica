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

    # Transport
    MCP_TRANSPORT: str = field(default_factory=lambda: _env("MCP_TRANSPORT", "stdio"))
    MCP_SSE_HOST: str = field(default_factory=lambda: _env("MCP_SSE_HOST", "0.0.0.0"))
    MCP_SSE_PORT: int = field(default_factory=lambda: int(_env("MCP_SSE_PORT", "8080")))

    # RabbitMQ streaming
    RABBITMQ_URL: str = field(default_factory=lambda: _env("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"))
    SIGNAL_QUEUE: str = field(default_factory=lambda: _env("SIGNAL_QUEUE", "signal.mcp"))
    SIGNAL_EXCHANGE: str = field(default_factory=lambda: _env("SIGNAL_EXCHANGE", "signal"))
    ANALYTICS_QUEUE: str = field(default_factory=lambda: _env("ANALYTICS_QUEUE", "analytics.mcp"))
    ANALYTICS_EXCHANGE: str = field(default_factory=lambda: _env("ANALYTICS_EXCHANGE", "analytics"))
    ANALYTICS_ROUTING_KEY: str = field(default_factory=lambda: _env("ANALYTICS_ROUTING_KEY", "signal.analytics.#"))
    STREAM_ENABLED: bool = field(default_factory=lambda: _env("STREAM_ENABLED", "false").lower() in ("true", "1", "yes"))
    STREAM_MAX_EVENTS_PER_SEC: int = field(default_factory=lambda: int(_env("STREAM_MAX_EVENTS_PER_SEC", "10")))
    STREAM_CACHE_SIZE_PER_SYMBOL: int = field(default_factory=lambda: int(_env("STREAM_CACHE_SIZE_PER_SYMBOL", "50")))
    DEDUP_MAXLEN: int = field(default_factory=lambda: int(_env("DEDUP_MAXLEN", "10000")))

    def __str__(self):
        return (
            f"MarketServer: {self.MARKETSERVER_BASE_URL}\n"
            f"Metrics Port: {self.METRICS_PORT}\n"
            f"Log Level: {self.LOG_LEVEL}\n"
            f"Risk Max Symbol Exposure: {self.RISK_MAX_SYMBOL_EXPOSURE}\n"
            f"Trade History Days Default: {self.TRADE_HISTORY_DAYS_DEFAULT}\n"
            f"Max Query Days: {self.MAX_QUERY_DAYS}\n"
            f"Resource Cache TTL: {self.RESOURCE_CACHE_TTL_SECONDS}s\n"
            f"MCP Transport: {self.MCP_TRANSPORT}\n"
            f"Stream Enabled: {self.STREAM_ENABLED}\n"
            f"RabbitMQ URL: {self.RABBITMQ_URL}"
        )
