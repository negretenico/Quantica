from unittest.mock import MagicMock, patch

from dlq.github_issues import GitHubIssueCreator


def _envelope():
    return {
        "original_queue": "signal.trade",
        "error": "ValueError: missing required field 'symbol'",
        "timestamp": "2026-08-15T12:34:56Z",
        "attempt_count": 4,
        "original_payload": {"price": 50000.0, "side": "BUY"},
    }


class TestGitHubIssueCreator:
    def test_create_issue_success(self):
        creator = GitHubIssueCreator(token="fake-token", repo="owner/repo")
        mock_response = MagicMock()
        mock_response.json.return_value = {"number": 42, "html_url": "https://github.com/owner/repo/issues/42"}
        mock_response.raise_for_status = MagicMock()

        creator._session = MagicMock()
        creator._session.post.return_value = mock_response

        result = creator.create_issue(_envelope())

        assert result is not None
        assert result["number"] == 42
        creator._session.post.assert_called_once()

        call_kwargs = creator._session.post.call_args
        posted_json = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert posted_json["title"] == "[DLQ] signal.trade: ValueError"
        assert "dlq" in posted_json["labels"]
        assert "automated" in posted_json["labels"]
        assert "signal.trade" in posted_json["body"]
        assert "missing required field" in posted_json["body"]

    def test_create_issue_api_error_returns_none(self):
        import requests

        creator = GitHubIssueCreator(token="fake-token", repo="owner/repo")
        creator._session = MagicMock()
        creator._session.post.side_effect = requests.RequestException("rate limited")

        result = creator.create_issue(_envelope())

        assert result is None

    def test_title_truncated_at_256_chars(self):
        creator = GitHubIssueCreator(token="fake-token", repo="owner/repo")
        mock_response = MagicMock()
        mock_response.json.return_value = {"number": 1}
        mock_response.raise_for_status = MagicMock()
        creator._session = MagicMock()
        creator._session.post.return_value = mock_response

        envelope = _envelope()
        envelope["error"] = "VeryLongErrorClass" + "X" * 300 + ": message"

        creator.create_issue(envelope)

        call_kwargs = creator._session.post.call_args
        posted_json = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert len(posted_json["title"]) <= 256

    def test_large_payload_truncated(self):
        creator = GitHubIssueCreator(token="fake-token", repo="owner/repo")
        mock_response = MagicMock()
        mock_response.json.return_value = {"number": 1}
        mock_response.raise_for_status = MagicMock()
        creator._session = MagicMock()
        creator._session.post.return_value = mock_response

        envelope = _envelope()
        envelope["original_payload"] = {"data": "x" * 5000}

        creator.create_issue(envelope)

        call_kwargs = creator._session.post.call_args
        posted_json = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "truncated" in posted_json["body"]
