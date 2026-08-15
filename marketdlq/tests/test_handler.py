from unittest.mock import MagicMock

from dlq.dedup import IssueDedupFilter
from dlq.handler import DlqHandler


def _envelope(queue="signal.trade", error="ValueError: bad"):
    return {
        "original_queue": queue,
        "error": error,
        "timestamp": "2026-08-15T12:00:00Z",
        "attempt_count": 3,
        "original_payload": {"symbol": "BTCUSDT"},
    }


class TestDlqHandler:
    def test_creates_issue_for_new_message(self):
        creator = MagicMock()
        creator.create_issue.return_value = {"number": 1}
        dedup = IssueDedupFilter()
        handler = DlqHandler(issue_creator=creator, dedup=dedup)

        handler.handle(_envelope())

        creator.create_issue.assert_called_once()

    def test_skips_duplicate_issue(self):
        creator = MagicMock()
        creator.create_issue.return_value = {"number": 1}
        dedup = IssueDedupFilter()
        handler = DlqHandler(issue_creator=creator, dedup=dedup)

        handler.handle(_envelope())
        handler.handle(_envelope())

        creator.create_issue.assert_called_once()

    def test_different_queues_create_separate_issues(self):
        creator = MagicMock()
        creator.create_issue.return_value = {"number": 1}
        dedup = IssueDedupFilter()
        handler = DlqHandler(issue_creator=creator, dedup=dedup)

        handler.handle(_envelope(queue="signal.trade"))
        handler.handle(_envelope(queue="signal.bard"))

        assert creator.create_issue.call_count == 2

    def test_handles_issue_creation_failure(self):
        creator = MagicMock()
        creator.create_issue.return_value = None
        dedup = IssueDedupFilter()
        handler = DlqHandler(issue_creator=creator, dedup=dedup)

        # Should not raise
        handler.handle(_envelope())
        creator.create_issue.assert_called_once()
