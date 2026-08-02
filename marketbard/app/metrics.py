import time

from prometheus_client import Counter, Histogram, Gauge, start_http_server

METRICS_PORT = 8001

tick_to_bard_latency = Histogram(
    "marketbard_tick_to_ingest_seconds",
    "Latency from Binance eventTime to bard signal ingestion",
    ["symbol"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)

signals_received_total = Counter(
    "marketbard_signals_received_total",
    "Total signal events received (before dedup)",
)

analytics_received_total = Counter(
    "marketbard_analytics_received_total",
    "Total analytics enrichment events received",
)

duplicates_dropped_total = Counter(
    "marketbard_duplicates_dropped_total",
    "Events dropped as duplicates",
    ["source"],
)

windows_processed_total = Counter(
    "marketbard_windows_processed_total",
    "Window batches processed",
    ["category"],
)

syntheses_completed_total = Counter(
    "marketbard_syntheses_completed_total",
    "Daily synthesis narratives completed",
)

event_buffer_size = Gauge(
    "marketbard_event_buffer_size",
    "Current number of events in the event buffer",
)

summary_buffer_size = Gauge(
    "marketbard_summary_buffer_size",
    "Current number of summaries in the summary buffer",
)


def observe_tick_to_bard(event: dict):
    event_time_ms = event.get("eventTime")
    if event_time_ms is None:
        return
    try:
        latency = time.time() - int(event_time_ms) / 1000.0
        if latency >= 0:
            tick_to_bard_latency.labels(symbol=event.get("symbol", "unknown")).observe(latency)
    except (ValueError, TypeError):
        pass


def start_metrics_server():
    start_http_server(METRICS_PORT)
