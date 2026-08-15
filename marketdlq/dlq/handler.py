import logging

from app.metrics import (
    dlq_duplicates_dropped_total,
    dlq_issue_errors_total,
    dlq_issues_created_total,
    dlq_messages_total,
    dlq_processing_seconds,
)
from dlq.dedup import IssueDedupFilter
from dlq.github_issues import GitHubIssueCreator

logger = logging.getLogger(__name__)


class DlqHandler:
    """Processes DLQ envelopes: logs a warning and creates a GitHub issue."""

    def __init__(self, issue_creator: GitHubIssueCreator, dedup: IssueDedupFilter):
        self._issue_creator = issue_creator
        self._dedup = dedup
        self._logged: set[str] = set()

    def handle(self, envelope: dict):
        original_queue = envelope.get("original_queue", "unknown")
        error = envelope.get("error", "unknown")
        timestamp = envelope.get("timestamp", "N/A")
        attempt_count = envelope.get("attempt_count", "N/A")

        dlq_messages_total.labels(original_queue=original_queue).inc()

        log_key = f"{original_queue}|{error}"
        if log_key not in self._logged:
            logger.warning(
                "DLQ message received — queue=%s error=%s timestamp=%s attempts=%s",
                original_queue,
                error,
                timestamp,
                attempt_count,
            )
            self._logged.add(log_key)

        if self._dedup.is_duplicate(envelope):
            dlq_duplicates_dropped_total.inc()
            logger.debug("Duplicate DLQ issue suppressed for queue=%s", original_queue)
            return

        with dlq_processing_seconds.time():
            result = self._issue_creator.create_issue(envelope)

        if result is not None:
            dlq_issues_created_total.labels(original_queue=original_queue).inc()
        else:
            dlq_issue_errors_total.inc()
