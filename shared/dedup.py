"""Bounded in-memory dedup filter, shared across all consumers."""

from collections import OrderedDict


class DedupFilter:
    """Rolling seen-set keyed on ``symbol|eventTime|type``.

    Thread-safe only if callers already serialise access (e.g. single
    RabbitMQ consumer callback).  The bound prevents unbounded growth;
    oldest entries are evicted FIFO.
    """

    def __init__(self, maxlen: int = 10_000):
        self._seen: OrderedDict[str, None] = OrderedDict()
        self._maxlen = maxlen

    @staticmethod
    def _key(event: dict) -> str:
        symbol = event.get("symbol", "")
        event_time = event.get("eventTime", "")
        event_type = event.get("type", "")
        return f"{symbol}|{event_time}|{event_type}"

    def is_duplicate(self, event: dict) -> bool:
        """Return *True* if this event has already been seen."""
        key = self._key(event)
        if key in self._seen:
            return True
        self._seen[key] = None
        if len(self._seen) > self._maxlen:
            self._seen.popitem(last=False)
        return False
