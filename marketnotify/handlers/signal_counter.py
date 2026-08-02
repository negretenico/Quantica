import threading


class SignalCounter:
    """Thread-safe counter for signal events. Resets on each digest read."""

    def __init__(self):
        self._lock = threading.Lock()
        self._count = 0

    def increment(self):
        with self._lock:
            self._count += 1

    def get_and_reset(self) -> int:
        with self._lock:
            count = self._count
            self._count = 0
            return count

    @property
    def count(self) -> int:
        with self._lock:
            return self._count
