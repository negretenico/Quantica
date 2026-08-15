import time
from collections import OrderedDict


class IssueDedupFilter:
    """Time-bounded dedup for GitHub issue creation.

    Keys on original_queue + error class + truncated error message so that
    repeated failures from the same root cause produce only one issue within
    the TTL window.
    """

    def __init__(self, ttl_hours: int = 24, maxlen: int = 1000):
        self._ttl_seconds = ttl_hours * 3600
        self._maxlen = maxlen
        self._seen: OrderedDict[str, float] = OrderedDict()

    @staticmethod
    def _key(envelope: dict) -> str:
        original_queue = envelope.get("original_queue", "unknown")
        error = envelope.get("error", "")
        # error format is "ErrorClass: message" — split to get class + prefix
        parts = error.split(":", 1)
        error_class = parts[0].strip()
        error_prefix = parts[1].strip()[:100] if len(parts) > 1 else ""
        return f"{original_queue}|{error_class}|{error_prefix}"

    def is_duplicate(self, envelope: dict) -> bool:
        key = self._key(envelope)
        now = time.monotonic()

        if key in self._seen:
            last_seen = self._seen[key]
            if now - last_seen < self._ttl_seconds:
                return True
            # TTL expired — remove and re-insert below
            del self._seen[key]

        # Evict oldest if at capacity
        while len(self._seen) >= self._maxlen:
            self._seen.popitem(last=False)

        self._seen[key] = now
        return False
