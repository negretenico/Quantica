import time

from prometheus_client import Counter, Histogram, start_http_server

METRICS_PORT = 8000

tick_to_trade_latency = Histogram(
    "markettrade_tick_to_trade_seconds",
    "Latency from Binance eventTime to trade decision",
    ["symbol"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)

decisions_total = Counter(
    "markettrade_decisions_total",
    "Trade decisions made",
    ["symbol", "action"],
)

risk_rejections_total = Counter(
    "markettrade_risk_rejections_total",
    "Trade proposals rejected by risk engine",
    ["symbol", "reason"],
)

events_received_total = Counter(
    "markettrade_events_received_total",
    "Total signal events received (before dedup)",
)

duplicates_dropped_total = Counter(
    "markettrade_duplicates_dropped_total",
    "Events dropped as duplicates",
)

outcome_records_total = Counter(
    "markettrade_outcome_records_total",
    "Decision records written for outcome tracking",
    ["symbol", "action"],
)

outcome_record_errors_total = Counter(
    "markettrade_outcome_record_errors_total",
    "Errors writing outcome records",
    ["symbol"],
)


def observe_tick_to_trade(event: dict):
    event_time_ms = event.get("eventTime")
    if event_time_ms is None:
        return
    try:
        latency = time.time() - int(event_time_ms) / 1000.0
        if latency >= 0:
            tick_to_trade_latency.labels(symbol=event.get("symbol", "unknown")).observe(latency)
    except (ValueError, TypeError):
        pass


def start_metrics_server():
    start_http_server(METRICS_PORT)
