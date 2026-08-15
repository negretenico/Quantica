from prometheus_client import Counter, Histogram, start_http_server

METRICS_PORT = 8000

dlq_messages_total = Counter(
    "marketdlq_messages_total",
    "DLQ messages received",
    ["original_queue"],
)

dlq_duplicates_dropped_total = Counter(
    "marketdlq_duplicates_dropped_total",
    "DLQ messages dropped as duplicate issues",
)

dlq_issues_created_total = Counter(
    "marketdlq_issues_created_total",
    "GitHub issues created from DLQ messages",
    ["original_queue"],
)

dlq_issue_errors_total = Counter(
    "marketdlq_issue_errors_total",
    "Errors creating GitHub issues",
)

dlq_processing_seconds = Histogram(
    "marketdlq_processing_seconds",
    "Time to process a DLQ message (log + issue creation)",
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)


def start_metrics_server():
    start_http_server(METRICS_PORT)
