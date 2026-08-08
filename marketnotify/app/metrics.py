from prometheus_client import Counter, Histogram, start_http_server

METRICS_PORT = 8000

notifications_sent_total = Counter(
    "marketnotify_notifications_sent_total",
    "Total notifications successfully sent",
)

notifications_failed_total = Counter(
    "marketnotify_notifications_failed_total",
    "Total notifications that failed to send",
)

events_received_total = Counter(
    "marketnotify_events_received_total",
    "Total events received across all queues",
    ["queue"],
)

duplicates_dropped_total = Counter(
    "marketnotify_duplicates_dropped_total",
    "Events dropped as duplicates",
    ["queue"],
)

notification_latency = Histogram(
    "marketnotify_notification_latency_seconds",
    "Time to send a notification via Discord webhook",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)


def start_metrics_server():
    start_http_server(METRICS_PORT)
