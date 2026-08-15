import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

_DEFAULT_DLQ_QUEUES = (
    "signal.analysis,signal.bard,signal.trade,"
    "analytics.trade,signal.notify,notifications.notify"
)


@dataclass
class Config:
    RABBITMQ_URL: str = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost/")
    DLQ_EXCHANGE: str = os.environ.get("DLQ_EXCHANGE", "dlq")
    DLQ_MONITOR_QUEUE: str = os.environ.get("DLQ_MONITOR_QUEUE", "dlq.monitor")
    DLQ_QUEUES: str = os.environ.get("DLQ_QUEUES", _DEFAULT_DLQ_QUEUES)
    GITHUB_TOKEN: str = os.environ.get("GITHUB_TOKEN", "")
    GITHUB_REPO: str = os.environ.get("GITHUB_REPO", "negretenico/Quantica-resilience")
    ISSUE_DEDUP_TTL_HOURS: int = int(os.environ.get("ISSUE_DEDUP_TTL_HOURS", "24"))
    ISSUE_DEDUP_MAXLEN: int = int(os.environ.get("ISSUE_DEDUP_MAXLEN", "1000"))

    def source_queues(self) -> list[str]:
        return [q.strip() for q in self.DLQ_QUEUES.split(",") if q.strip()]

    def __str__(self):
        return (
            f"RabbitMQ: {self.RABBITMQ_URL}\n"
            f"DLQ Exchange: {self.DLQ_EXCHANGE}\n"
            f"Monitor Queue: {self.DLQ_MONITOR_QUEUE}\n"
            f"Source Queues: {self.source_queues()}\n"
            f"GitHub Repo: {self.GITHUB_REPO}\n"
            f"Dedup TTL: {self.ISSUE_DEDUP_TTL_HOURS}h"
        )
