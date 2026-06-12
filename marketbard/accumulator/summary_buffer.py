import threading
import logging
from collections import deque

logger = logging.getLogger(__name__)


class SummaryBuffer:
    """
    Thread-safe rolling buffer for per-window summaries.
    Bounded at maxlen — oldest entry is evicted when full.
    """

    def __init__(self, maxlen: int):
        self._buffer: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def add(self, summary: dict):
        with self._lock:
            self._buffer.append(summary)
            logger.debug(f"SummaryBuffer: added summary, size={len(self._buffer)}")

    def drain(self) -> list:
        with self._lock:
            items = list(self._buffer)
            self._buffer.clear()
            logger.debug(f"SummaryBuffer: drained {len(items)} summaries")
            return items
