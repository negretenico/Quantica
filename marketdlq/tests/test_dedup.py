import time
from unittest.mock import patch

from dlq.dedup import IssueDedupFilter


def _envelope(queue="signal.trade", error="ValueError: missing field"):
    return {
        "original_queue": queue,
        "error": error,
        "timestamp": "2026-08-15T12:00:00Z",
        "attempt_count": 3,
        "original_payload": {"symbol": "BTCUSDT"},
    }


class TestIssueDedupFilter:
    def test_first_message_is_not_duplicate(self):
        f = IssueDedupFilter()
        assert f.is_duplicate(_envelope()) is False

    def test_same_message_within_ttl_is_duplicate(self):
        f = IssueDedupFilter()
        f.is_duplicate(_envelope())
        assert f.is_duplicate(_envelope()) is True

    def test_different_queue_is_not_duplicate(self):
        f = IssueDedupFilter()
        f.is_duplicate(_envelope(queue="signal.trade"))
        assert f.is_duplicate(_envelope(queue="signal.bard")) is False

    def test_different_error_class_is_not_duplicate(self):
        f = IssueDedupFilter()
        f.is_duplicate(_envelope(error="ValueError: bad"))
        assert f.is_duplicate(_envelope(error="TypeError: bad")) is False

    def test_expired_ttl_allows_new_issue(self):
        f = IssueDedupFilter(ttl_hours=1)
        f.is_duplicate(_envelope())

        # Simulate TTL expiry by shifting the stored timestamp back
        key = list(f._seen.keys())[0]
        f._seen[key] = time.monotonic() - 3601

        assert f.is_duplicate(_envelope()) is False

    def test_maxlen_eviction(self):
        f = IssueDedupFilter(maxlen=2)
        f.is_duplicate(_envelope(queue="q1"))
        f.is_duplicate(_envelope(queue="q2"))
        # Adding a third should evict q1
        f.is_duplicate(_envelope(queue="q3"))
        # q1 should no longer be tracked
        assert f.is_duplicate(_envelope(queue="q1")) is False

    def test_key_uses_error_prefix(self):
        f = IssueDedupFilter()
        long_msg = "x" * 200
        f.is_duplicate(_envelope(error=f"ValueError: {long_msg}"))
        # Same prefix (first 100 chars) should match
        assert f.is_duplicate(_envelope(error=f"ValueError: {long_msg}")) is True

    def test_missing_fields_handled(self):
        f = IssueDedupFilter()
        assert f.is_duplicate({}) is False
        assert f.is_duplicate({}) is True
