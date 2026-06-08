import threading
import logging

logger = logging.getLogger(__name__)


class EventBuffer:
    def __init__(self):
        self._buffer: list = []
        self._lock = threading.Lock()

    def add(self, event: dict):
        with self._lock:
            self._buffer.append(event)
            logger.debug(f"EventBuffer: added event, buffer size={len(self._buffer)}")

    def drain(self) -> list:
        with self._lock:
            batch = self._buffer[:]
            self._buffer = []
            logger.debug(f"EventBuffer: drained {len(batch)} events")
            return batch
