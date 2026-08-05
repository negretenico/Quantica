import random
import time
import logging
from dataclasses import dataclass

from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

retries_total = Counter(
    "rabbitmq_consumer_retries_total",
    "Retry attempts before dead-letter",
    ["queue"],
)
handler_errors_total = Counter(
    "rabbitmq_consumer_handler_errors_total",
    "Total handler errors (includes retried and dead-lettered)",
    ["queue"],
)
retry_backoff_seconds = Histogram(
    "rabbitmq_consumer_retry_backoff_seconds",
    "Backoff delay applied between retry attempts",
    ["queue"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 30.0],
)


def _compute_backoff(attempt: int, base_delay: float, max_delay: float = 30.0) -> float:
    """Exponential backoff with full jitter.

    delay = random_between(0, min(max_delay, base_delay * 2^attempt))
    """
    exp_delay = min(max_delay, base_delay * (2 ** attempt))
    return random.uniform(0, exp_delay)


@dataclass(frozen=True)
class RetryPolicy:
    """Encapsulates retry-with-backoff behaviour for message handlers.

    Follows the same delegation pattern as QueueBinding — the consumer
    calls ``execute()`` instead of owning the retry loop inline.
    """

    max_retries: int = 3
    base_delay_seconds: float = 1.0

    def execute(self, handler, payload: dict, queue: str) -> tuple[bool, Exception | None, int]:
        """Run *handler(payload)* with retries and exponential backoff.

        Returns ``(success, last_error, attempts)`` so the caller can
        decide on ack/nack/DLQ without knowing retry internals.
        """
        last_error = None
        for attempt in range(1, self.max_retries + 2):
            try:
                handler(payload)
                return True, None, attempt
            except Exception as e:
                last_error = e
                handler_errors_total.labels(queue=queue).inc()
                logger.error(
                    "Error processing message from '%s' "
                    "(attempt %d/%d): %s",
                    queue, attempt, self.max_retries + 1, e,
                )
                if attempt <= self.max_retries:
                    retries_total.labels(queue=queue).inc()
                    delay = _compute_backoff(attempt - 1, self.base_delay_seconds)
                    retry_backoff_seconds.labels(queue=queue).observe(delay)
                    logger.info(
                        "Retrying '%s' in %.2fs (attempt %d/%d)",
                        queue, delay, attempt + 1, self.max_retries + 1,
                    )
                    time.sleep(delay)

        return False, last_error, self.max_retries + 1
