import json
import logging
import threading
import time
import urllib.request
import urllib.error
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from queue import Empty, PriorityQueue
from typing import Protocol

from shared.blob import get_store

logger = logging.getLogger(__name__)


def create_lookback(config, outcome_tracker=None):
    """Factory: build a (PriceLookback, InMemoryPriceCache) pair from config, or (None, None) if disabled."""
    if not config.lookback.ENABLED:
        logger.info("PriceLookback disabled")
        return None, None

    cache = InMemoryPriceCache()
    source = BinancePriceSource(config.lookback.BINANCE_BASE_URL, config.lookback.BINANCE_TIMEOUT)
    store = get_store(config.blob_store.BACKEND, config.lookback.STORE_PATH)
    lookback = PriceLookback(
        windows=config.lookback.WINDOWS,
        price_source=source,
        cache=cache,
        outcome_store=store,
        max_pending=config.lookback.MAX_PENDING,
        outcome_tracker=outcome_tracker,
    )
    logger.info("PriceLookback enabled (windows=%s)", config.lookback.WINDOWS)
    return lookback, cache


class PriceSource(Protocol):
    def get_price(self, symbol: str, timestamp_epoch_s: float) -> float | None: ...


class BinancePriceSource:
    def __init__(self, base_url: str = "https://api.binance.com", timeout: int = 5):
        self._base_url = base_url
        self._timeout = timeout

    def get_price(self, symbol: str, timestamp_epoch_s: float) -> float | None:
        start_ms = int(timestamp_epoch_s * 1000)
        url = (
            f"{self._base_url}/api/v3/klines"
            f"?symbol={symbol}&interval=1m&startTime={start_ms}&limit=1"
        )
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read())
            if data and len(data) > 0 and len(data[0]) >= 5:
                return float(data[0][4])  # close price
        except Exception as e:
            logger.debug("Binance price fetch failed for %s: %s", symbol, e)
        return None


class InMemoryPriceCache:
    def __init__(self, maxlen_per_symbol: int = 500):
        self._data: dict[str, deque[tuple[float, float]]] = {}
        self._maxlen = maxlen_per_symbol
        self._lock = threading.Lock()

    def record(self, symbol: str, timestamp_epoch_s: float, price: float) -> None:
        with self._lock:
            if symbol not in self._data:
                self._data[symbol] = deque(maxlen=self._maxlen)
            self._data[symbol].append((timestamp_epoch_s, price))

    def get_price(self, symbol: str, timestamp_epoch_s: float, tolerance_s: float = 5.0) -> float | None:
        with self._lock:
            entries = self._data.get(symbol)
            if not entries:
                return None
            best_ts, best_price = None, None
            best_diff = float("inf")
            for ts, price in entries:
                diff = abs(ts - timestamp_epoch_s)
                if diff < best_diff:
                    best_diff = diff
                    best_ts = ts
                    best_price = price
            if best_diff <= tolerance_s:
                return best_price
        return None


@dataclass(frozen=True)
class LookbackTask:
    due_time: float
    symbol: str
    action: str
    entry_price: float
    decision_time: float
    window: int

    def __lt__(self, other):
        return self.due_time < other.due_time


class PriceLookback:
    def __init__(
        self,
        windows: list[int],
        price_source: PriceSource,
        cache: InMemoryPriceCache,
        outcome_store,
        max_pending: int = 5000,
        outcome_tracker=None,
    ):
        self._windows = windows
        self._source = price_source
        self._cache = cache
        self._store = outcome_store
        self._max_pending = max_pending
        self._tracker = outcome_tracker
        self._queue: PriorityQueue[LookbackTask] = PriorityQueue()
        self._pending_count = 0
        self._count_lock = threading.Lock()
        self._stop = threading.Event()

        self._thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._thread.start()
        logger.info("PriceLookback scheduler started (windows=%s)", windows)

    def schedule(self, decision: dict) -> None:
        from app.metrics import lookback_scheduled_total, lookback_dropped_total

        now = time.time()
        decision_time = now

        for window in self._windows:
            with self._count_lock:
                if self._pending_count >= self._max_pending:
                    lookback_dropped_total.inc()
                    logger.debug("Lookback task dropped — max_pending reached")
                    continue
                self._pending_count += 1

            task = LookbackTask(
                due_time=decision_time + window,
                symbol=decision["symbol"],
                action=decision["action"],
                entry_price=decision["entry_price"],
                decision_time=decision_time,
                window=window,
            )
            self._queue.put(task)
            lookback_scheduled_total.labels(
                symbol=decision["symbol"], window=str(window)
            ).inc()

    def _run_scheduler(self) -> None:
        while not self._stop.is_set():
            try:
                task = self._queue.get(timeout=5.0)
            except Empty:
                continue

            wait = task.due_time - time.time()
            if wait > 0:
                self._stop.wait(wait)
                if self._stop.is_set():
                    break

            self._execute_task(task)

    def _execute_task(self, task: LookbackTask) -> None:
        from app.metrics import (
            lookback_completed_total,
            lookback_failed_total,
            lookback_latency,
        )

        start = time.time()

        price = self._cache.get_price(task.symbol, task.due_time)
        source = "cache"

        if price is None:
            price = self._source.get_price(task.symbol, task.due_time)
            source = "binance"

        elapsed = time.time() - start

        if price is None:
            lookback_failed_total.labels(
                symbol=task.symbol, window=str(task.window)
            ).inc()
            logger.debug(
                "Lookback failed — symbol=%s window=%d (no price from cache or binance)",
                task.symbol, task.window,
            )
            with self._count_lock:
                self._pending_count -= 1
            return

        lookback_latency.labels(source=source).observe(elapsed)
        lookback_completed_total.labels(
            symbol=task.symbol, window=str(task.window), source=source
        ).inc()

        record = {
            "type": "price_lookback",
            "symbol": task.symbol,
            "action": task.action,
            "entry_price": task.entry_price,
            "decision_time": datetime.fromtimestamp(task.decision_time, tz=timezone.utc).isoformat(),
            "window_seconds": task.window,
            "outcome_price": price,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "price_source": source,
        }

        try:
            self._store.write(record)
        except Exception:
            logger.exception("Failed to write lookback record for %s", task.symbol)

        if self._tracker is not None:
            try:
                self._tracker.evaluate(record)
            except Exception:
                logger.exception("OutcomeTracker evaluation failed for %s", task.symbol)

        with self._count_lock:
            self._pending_count -= 1

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=10)
