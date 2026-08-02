import logging

import requests

from .channel import NotificationChannel, NotificationMessage

logger = logging.getLogger(__name__)


class DiscordWebhookChannel(NotificationChannel):
    def __init__(self, webhook_url: str):
        self._webhook_url = webhook_url

    def send(self, message: NotificationMessage) -> None:
        embed = {
            "title": message.title,
            "description": message.body,
            "color": int(message.color, 16),
        }
        if message.fields:
            embed["fields"] = [
                {"name": name, "value": value, "inline": True}
                for name, value in message.fields
            ]

        payload = {"embeds": [embed]}

        resp = requests.post(self._webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.debug("Discord webhook sent: %s", message.title)
