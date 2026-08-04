import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class SignalSnapshot:
    received: int
    duplicates: int
    counted: int


class SignalCounter:
    """Thread-safe counter for signal events. Resets on each digest read."""

    def __init__(self):
        self._lock = threading.Lock()
        self._received = 0
        self._duplicates = 0
        self._counted = 0

    def record_received(self):
        with self._lock:
            self._received += 1

    def record_duplicate(self):
        with self._lock:
            self._duplicates += 1

    def record_counted(self):
        with self._lock:
            self._counted += 1

    def snapshot_and_reset(self) -> SignalSnapshot:
        with self._lock:
            snap = SignalSnapshot(
                received=self._received,
                duplicates=self._duplicates,
                counted=self._counted,
            )
            self._received = 0
            self._duplicates = 0
            self._counted = 0
            return snap
