import time
from collections import deque


class TradeRateLimiter:

    def __init__(self, max_per_minute: int = 10, window_seconds: float = 60.0):
        self._max = max_per_minute
        self._window = window_seconds
        self._windows: dict[str, deque[float]] = {}

    def check(self, symbol: str, now: float | None = None) -> tuple[bool, str | None]:
        if now is None:
            now = time.time()

        dq = self._windows.setdefault(symbol, deque())

        while dq and dq[0] <= now - self._window:
            dq.popleft()

        if len(dq) >= self._max:
            return False, f"rate_limited: {len(dq)}/{self._max} in {self._window:.0f}s"

        dq.append(now)
        return True, None
