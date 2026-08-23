"""Real-time RabbitMQ signal stream feeding an in-memory cache.

Uses the same RabbitConsumer + DedupFilter pattern as markettrade/marketnotify.
Resources can read from this cache for fresher data when streaming is enabled.
"""

from __future__ import annotations

import logging
import time
import threading
from collections import deque

from shared.rabbitmq.consumer import RabbitConsumer, ConsumerConfig
from shared.dedup import DedupFilter

from app.config import Config
from app.metrics import (
    stream_events_received_total,
    stream_events_deduplicated_total,
    stream_events_rate_limited_total,
)

logger = logging.getLogger(__name__)


class TokenBucket:
    """Simple token bucket rate limiter. Thread-safe."""

    def __init__(self, rate: float, capacity: float | None = None):
        self._rate = rate
        self._capacity = capacity if capacity is not None else rate
        self._tokens = self._capacity
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def consume(self) -> bool:
        """Try to consume one token. Returns True if allowed."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
            self._last_refill = now

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False


class SignalStream:
    """Consumes signals from RabbitMQ and maintains an in-memory event cache.

    Each symbol stores a bounded deque of the last N events.
    """

    def __init__(self, config: Config):
        self._config = config
        self._cache: dict[str, deque[dict]] = {}
        self._lock = threading.Lock()
        self._max_per_symbol = config.STREAM_CACHE_SIZE_PER_SYMBOL

        self._dedup = DedupFilter(maxlen=config.DEDUP_MAXLEN)
        self._rate_limiter = TokenBucket(rate=config.STREAM_MAX_EVENTS_PER_SEC)

        # Signal consumer (fanout exchange)
        self._signal_consumer = RabbitConsumer(ConsumerConfig(
            url=config.RABBITMQ_URL,
            queue=config.SIGNAL_QUEUE,
            exchange=config.SIGNAL_EXCHANGE,
            exchange_type="fanout",
            routing_key=None,
        ))
        self._signal_consumer.register_handler(self._handle_signal)

        # Analytics consumer (topic exchange)
        self._analytics_consumer = RabbitConsumer(ConsumerConfig(
            url=config.RABBITMQ_URL,
            queue=config.ANALYTICS_QUEUE,
            exchange=config.ANALYTICS_EXCHANGE,
            exchange_type="topic",
            routing_key=config.ANALYTICS_ROUTING_KEY,
        ))
        self._analytics_consumer.register_handler(self._handle_analytics)

    def start(self):
        """Start both consumer threads (daemon)."""
        self._signal_consumer.start_consuming()
        self._analytics_consumer.start_consuming()
        logger.info("SignalStream started (signal=%s, analytics=%s)",
                    self._config.SIGNAL_QUEUE, self._config.ANALYTICS_QUEUE)

    def _handle_signal(self, payload: dict, queue: str):
        """Handler for signal fanout events."""
        self._process_event(payload, source="signal")

    def _handle_analytics(self, payload: dict, queue: str):
        """Handler for analytics topic events."""
        self._process_event(payload, source="analytics")

    def _process_event(self, payload: dict, source: str):
        """Dedup, rate limit, and cache an event."""
        stream_events_received_total.labels(source=source).inc()

        if self._dedup.is_duplicate(payload):
            stream_events_deduplicated_total.labels(source=source).inc()
            return

        if not self._rate_limiter.consume():
            stream_events_rate_limited_total.labels(source=source).inc()
            return

        symbol = payload.get("symbol", "UNKNOWN")
        with self._lock:
            if symbol not in self._cache:
                self._cache[symbol] = deque(maxlen=self._max_per_symbol)
            self._cache[symbol].append(payload)

    def has_data(self) -> bool:
        """Return True if the cache has any events."""
        with self._lock:
            return len(self._cache) > 0

    def get_latest(self, symbol: str) -> list[dict]:
        """Return cached events for a specific symbol."""
        with self._lock:
            dq = self._cache.get(symbol)
            if dq is None:
                return []
            return list(dq)

    def get_all_latest(self) -> list[dict]:
        """Return all cached events across all symbols as a flat list."""
        with self._lock:
            result = []
            for dq in self._cache.values():
                result.extend(dq)
            return result


# Module-level singleton, set by run.py when streaming is enabled
_stream_instance: SignalStream | None = None


def set_stream_instance(stream: SignalStream):
    """Register the global stream instance."""
    global _stream_instance
    _stream_instance = stream


def get_stream_instance() -> SignalStream | None:
    """Get the global stream instance (None if streaming is disabled)."""
    return _stream_instance
