import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    DISCORD_WEBHOOK_URL: str = os.environ.get('DISCORD_WEBHOOK_URL', '')
    RABBITMQ_URL: str = os.environ.get('RABBITMQ_URL', 'amqp://guest:guest@localhost/')
    NOTIFY_EXCHANGE: str = os.environ.get('NOTIFY_EXCHANGE', 'notifications')
    SIGNAL_EXCHANGE: str = os.environ.get('SIGNAL_EXCHANGE', 'signal')
    SIGNAL_QUEUE: str = os.environ.get('SIGNAL_NOTIFY_QUEUE', 'signal.notify')
    NOTIFY_QUEUE: str = os.environ.get('NOTIFY_QUEUE', 'notifications.notify')
    SYNTHESIS_HOUR: int = int(os.environ.get('SYNTHESIS_HOUR', '16'))
    HEALTH_DIGEST_INTERVAL_MINUTES: int = int(os.environ.get('HEALTH_DIGEST_INTERVAL_MINUTES', '60'))
    MAX_RETRIES: int = int(os.environ.get('RABBITMQ_MAX_RETRIES', '3'))
    RETRY_BASE_DELAY: float = float(os.environ.get('RABBITMQ_RETRY_BASE_DELAY', '1.0'))
    PROMETHEUS_TARGETS: str = os.environ.get(
        'PROMETHEUS_TARGETS',
        'http://localhost:8000/metrics,http://localhost:8001/metrics',
    )

    def prometheus_target_list(self) -> list[str]:
        return [t.strip() for t in self.PROMETHEUS_TARGETS.split(',') if t.strip()]

    def __str__(self):
        return (
            f"RabbitMQ: {self.RABBITMQ_URL}\n"
            f"Discord Webhook: {'configured' if self.DISCORD_WEBHOOK_URL else 'NOT SET'}\n"
            f"Health Digest Interval: {self.HEALTH_DIGEST_INTERVAL_MINUTES}m"
        )
