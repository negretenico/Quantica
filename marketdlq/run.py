import logging
import threading

from app.config import Config
from app.metrics import start_metrics_server
from dlq.consumer import DlqConsumer
from dlq.dedup import IssueDedupFilter
from dlq.github_issues import GitHubIssueCreator
from dlq.handler import DlqHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    config = Config()
    logger.info("Starting marketdlq\n%s", config)

    issue_creator = GitHubIssueCreator(
        token=config.GITHUB_TOKEN,
        repo=config.GITHUB_REPO,
    )
    dedup = IssueDedupFilter(
        ttl_hours=config.ISSUE_DEDUP_TTL_HOURS,
        maxlen=config.ISSUE_DEDUP_MAXLEN,
    )
    handler = DlqHandler(issue_creator=issue_creator, dedup=dedup)

    consumer = DlqConsumer(
        url=config.RABBITMQ_URL,
        exchange=config.DLQ_EXCHANGE,
        queue=config.DLQ_MONITOR_QUEUE,
        routing_keys=config.source_queues(),
    )
    consumer.register_handler(handler.handle)

    start_metrics_server()
    logger.info("Prometheus metrics server started on :8000")

    consumer.start_consuming()
    threading.Event().wait()


if __name__ == "__main__":
    main()
