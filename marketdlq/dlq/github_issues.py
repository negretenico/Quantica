import json
import logging

import requests

logger = logging.getLogger(__name__)


class GitHubIssueCreator:
    """Creates GitHub issues from DLQ envelopes via the REST API."""

    _API_BASE = "https://api.github.com"

    def __init__(self, token: str, repo: str):
        self._token = token
        self._repo = repo
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def create_issue(self, envelope: dict) -> dict | None:
        original_queue = envelope.get("original_queue", "unknown")
        error = envelope.get("error", "unknown error")
        timestamp = envelope.get("timestamp", "N/A")
        attempt_count = envelope.get("attempt_count", "N/A")
        original_payload = envelope.get("original_payload", {})

        error_class = error.split(":", 1)[0].strip()
        title = f"[DLQ] {original_queue}: {error_class}"[:256]

        payload_json = json.dumps(original_payload, indent=2, default=str)
        if len(payload_json) > 3000:
            payload_json = payload_json[:3000] + "\n... (truncated)"

        body = (
            "## Dead-Lettered Message\n\n"
            "| Field | Value |\n"
            "|---|---|\n"
            f"| Original Queue | `{original_queue}` |\n"
            f"| Error | `{error}` |\n"
            f"| Timestamp | `{timestamp}` |\n"
            f"| Attempt Count | `{attempt_count}` |\n\n"
            "### Original Payload\n"
            f"```json\n{payload_json}\n```\n"
        )

        url = f"{self._API_BASE}/repos/{self._repo}/issues"
        data = {
            "title": title,
            "body": body,
            "labels": ["dlq", "automated"],
        }

        try:
            resp = self._session.post(url, json=data, timeout=30)
            resp.raise_for_status()
            issue = resp.json()
            logger.info(
                "Created GitHub issue #%s for DLQ message from '%s'",
                issue.get("number"),
                original_queue,
            )
            return issue
        except requests.RequestException as e:
            logger.error("Failed to create GitHub issue: %s", e)
            return None
