from unittest.mock import patch, MagicMock

from shared.notifications import (
    DiscordWebhookChannel,
    NotificationChannel,
    NotificationMessage,
)


class TestNotificationMessage:
    def test_defaults(self):
        msg = NotificationMessage(title="t", body="b")
        assert msg.fields == []
        assert msg.color == "00ff00"

    def test_custom_fields(self):
        msg = NotificationMessage(
            title="t", body="b", fields=[("k", "v")], color="ff0000"
        )
        assert msg.fields == [("k", "v")]
        assert msg.color == "ff0000"


class TestDiscordWebhookChannel:
    def test_is_notification_channel(self):
        channel = DiscordWebhookChannel("https://example.com/webhook")
        assert isinstance(channel, NotificationChannel)

    @patch("shared.notifications.discord_webhook.requests.post")
    def test_send_posts_embed(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        channel = DiscordWebhookChannel("https://example.com/webhook")
        msg = NotificationMessage(
            title="Test Title",
            body="Test Body",
            fields=[("Symbol", "BTCUSDT"), ("Action", "BUY")],
            color="ff5733",
        )
        channel.send(msg)

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://example.com/webhook"

        payload = call_args[1]["json"]
        embed = payload["embeds"][0]
        assert embed["title"] == "Test Title"
        assert embed["description"] == "Test Body"
        assert embed["color"] == 0xFF5733
        assert len(embed["fields"]) == 2
        assert embed["fields"][0]["name"] == "Symbol"
        assert embed["fields"][0]["value"] == "BTCUSDT"
        assert embed["fields"][0]["inline"] is True

    @patch("shared.notifications.discord_webhook.requests.post")
    def test_send_no_fields(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        channel = DiscordWebhookChannel("https://example.com/webhook")
        msg = NotificationMessage(title="T", body="B")
        channel.send(msg)

        payload = mock_post.call_args[1]["json"]
        embed = payload["embeds"][0]
        assert "fields" not in embed

    @patch("shared.notifications.discord_webhook.requests.post")
    def test_send_raises_on_http_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("HTTP 500")
        mock_post.return_value = mock_resp

        channel = DiscordWebhookChannel("https://example.com/webhook")
        msg = NotificationMessage(title="T", body="B")
        try:
            channel.send(msg)
            assert False, "Expected exception"
        except Exception as e:
            assert "HTTP 500" in str(e)
