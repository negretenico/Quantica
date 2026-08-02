import datetime
import logging
import threading
from zoneinfo import ZoneInfo

import requests

from shared.notifications import NotificationChannel, NotificationMessage

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")


class HealthDigestThread:
    def __init__(
        self,
        channel: NotificationChannel,
        signal_counter,
        interval_minutes: int,
        synthesis_hour: int,
        prometheus_targets: list[str],
    ):
        self._channel = channel
        self._signal_counter = signal_counter
        self._interval_minutes = interval_minutes
        self._synthesis_hour = synthesis_hour
        self._prometheus_targets = prometheus_targets
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, name="health_digest", daemon=True)
        self._thread.start()
        logger.info("Health digest thread started (interval=%dm)", self._interval_minutes)

    def _run(self):
        while True:
            threading.Event().wait(timeout=self._interval_minutes * 60)
            try:
                self._send_digest()
            except Exception:
                logger.exception("Error sending health digest")

    def _send_digest(self):
        now = datetime.datetime.now(_ET)
        event_count = self._signal_counter.get_and_reset()

        target = now.replace(hour=self._synthesis_hour, minute=0, second=0, microsecond=0)
        if now >= target:
            target += datetime.timedelta(days=1)
        hours_until = (target - now).total_seconds() / 3600

        service_health = self._scrape_targets()

        fields = [
            ("Events (last period)", str(event_count)),
            ("Hours to synthesis", f"{hours_until:.1f}h"),
        ]
        for target_url, healthy in service_health:
            name = target_url.split("//")[-1].split("/")[0]
            fields.append((name, "UP" if healthy else "DOWN"))

        color = "00ff00" if all(h for _, h in service_health) else "ff0000"

        message = NotificationMessage(
            title="Quantica Health Digest",
            body=f"Status as of {now.strftime('%Y-%m-%d %H:%M ET')}",
            fields=fields,
            color=color,
        )
        self._channel.send(message)
        logger.info("Health digest sent: %d events, %d targets checked", event_count, len(service_health))

    def _scrape_targets(self) -> list[tuple[str, bool]]:
        results = []
        for target_url in self._prometheus_targets:
            try:
                resp = requests.get(target_url, timeout=5)
                results.append((target_url, resp.status_code == 200))
            except Exception:
                results.append((target_url, False))
        return results
