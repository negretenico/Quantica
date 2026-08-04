import time

from prometheus_client import Counter, Histogram, start_http_server

METRICS_PORT = 8000

events_consumed_total = Counter(
    "marketanalysis_events_consumed_total",
    "Total signal events received (before dedup)",
)

duplicates_dropped_total = Counter(
    "marketanalysis_duplicates_dropped_total",
    "Events dropped as duplicates",
)

clusters_computed_total = Counter(
    "marketanalysis_clusters_computed_total",
    "Events that received a cluster label",
    ["symbol", "cluster_id"],
)

anomalies_detected_total = Counter(
    "marketanalysis_anomalies_detected_total",
    "Events with anomaly_score above threshold",
    ["symbol"],
)

errors_total = Counter(
    "marketanalysis_errors_total",
    "Errors during event processing",
)

processing_latency = Histogram(
    "marketanalysis_processing_seconds",
    "Time spent in mini_batch + publish per event",
    ["symbol"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1),
)

tick_to_analysis_latency = Histogram(
    "marketanalysis_tick_to_analysis_seconds",
    "Latency from Binance eventTime to analysis publish",
    ["symbol"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)


def observe_tick_to_analysis(event: dict):
    event_time_ms = event.get("eventTime")
    if event_time_ms is None:
        return
    try:
        latency = time.time() - int(event_time_ms) / 1000.0
        if latency >= 0:
            tick_to_analysis_latency.labels(
                symbol=event.get("symbol", "unknown")
            ).observe(latency)
    except (ValueError, TypeError):
        pass


def start_metrics_server():
    start_http_server(METRICS_PORT)
