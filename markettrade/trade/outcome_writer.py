import logging
import threading
from dataclasses import asdict

from trade.outcome_tracker import OutcomeRecord

logger = logging.getLogger(__name__)


class OutcomeWriter:
    """Buffers OutcomeRecords and flushes to a blob store on count or time threshold."""

    def __init__(
        self,
        store,
        flush_count: int = 10,
        flush_interval_seconds: float = 60.0,
    ):
        self._store = store
        self._flush_count = flush_count
        self._flush_interval = flush_interval_seconds
        self._buffer: list[OutcomeRecord] = []
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._start_timer()

    def write(self, record: OutcomeRecord) -> None:
        with self._lock:
            self._buffer.append(record)
            if len(self._buffer) >= self._flush_count:
                self._flush_locked()

    def _start_timer(self) -> None:
        self._timer = threading.Timer(self._flush_interval, self._flush_on_timer)
        self._timer.daemon = True
        self._timer.start()

    def _flush_on_timer(self) -> None:
        with self._lock:
            self._flush_locked()
        self._start_timer()

    def _flush_locked(self) -> None:
        """Flush buffer to store. Must be called with self._lock held."""
        from app.metrics import (
            outcome_flush_total,
            outcome_flush_size,
            outcome_flush_errors_total,
        )

        if not self._buffer:
            return

        records = list(self._buffer)
        self._buffer.clear()

        for rec in records:
            try:
                self._store.write(asdict(rec))
            except Exception:
                outcome_flush_errors_total.inc()
                logger.exception("Failed to flush outcome record: %s", rec.symbol)

        outcome_flush_total.inc()
        outcome_flush_size.observe(len(records))
        logger.debug("Flushed %d outcome records to store", len(records))

    def flush(self) -> None:
        """Force flush — for shutdown or testing."""
        with self._lock:
            self._flush_locked()

    def stop(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
        self.flush()
