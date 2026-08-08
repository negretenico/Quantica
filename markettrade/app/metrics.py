import time

from prometheus_client import Counter, Gauge, Histogram, start_http_server

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

risk_evaluations_total = Counter(
    "markettrade_risk_evaluations_total",
    "Total risk evaluations by result",
    ["result"],
)

risk_sized_quantity = Histogram(
    "markettrade_risk_sized_quantity",
    "Sized quantity of approved trades after risk adjustment",
    buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000),
)

risk_exposure_ratio = Gauge(
    "markettrade_risk_exposure_ratio",
    "Current symbol exposure as ratio of max allowed",
    ["symbol"],
)

events_received_total = Counter(
    "markettrade_events_received_total",
    "Total signal events received (before dedup)",
)

duplicates_dropped_total = Counter(
    "markettrade_duplicates_dropped_total",
    "Events dropped as duplicates",
)

validation_errors_total = Counter(
    "markettrade_validation_errors_total",
    "Events rejected by schema validation",
    ["reason"],
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

lookback_scheduled_total = Counter(
    "markettrade_lookback_scheduled_total",
    "Price lookback tasks scheduled",
    ["symbol", "window"],
)

lookback_completed_total = Counter(
    "markettrade_lookback_completed_total",
    "Price lookback tasks completed",
    ["symbol", "window", "source"],
)

lookback_failed_total = Counter(
    "markettrade_lookback_failed_total",
    "Price lookback tasks that failed to get a price",
    ["symbol", "window"],
)

lookback_dropped_total = Counter(
    "markettrade_lookback_dropped_total",
    "Lookback tasks dropped due to max_pending cap",
)

lookback_latency = Histogram(
    "markettrade_lookback_fetch_seconds",
    "Time to fetch outcome price",
    ["source"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)

lookback_pnl = Histogram(
    "markettrade_lookback_pnl_pct",
    "PnL percentage of lookback outcomes",
    ["symbol", "window", "action"],
    buckets=(-0.05, -0.02, -0.01, -0.005, 0, 0.005, 0.01, 0.02, 0.05),
)

near_limit_alerts_total = Counter(
    "markettrade_near_limit_alerts_total",
    "Near-limit exposure alerts fired",
    ["symbol"],
)

near_limit_active_symbols = Gauge(
    "markettrade_near_limit_active_symbols",
    "Number of symbols currently in near-limit state",
)

near_limit_ratio = Gauge(
    "markettrade_near_limit_ratio",
    "Exposure ratio when near-limit alert fires",
    ["symbol"],
)

rate_limited_total = Counter(
    "markettrade_rate_limited_total",
    "Decisions rate-limited per symbol",
    ["symbol"],
)

rate_limiter_utilization = Gauge(
    "markettrade_rate_limiter_utilization",
    "Current window usage as fraction of max",
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


def observe_risk_evaluation(risk_decision, symbol, risk_engine, max_exposure):
    result_label = "approved" if risk_decision.approved else "rejected"
    risk_evaluations_total.labels(result=result_label).inc()

    if risk_decision.approved:
        risk_sized_quantity.observe(risk_decision.sized_quantity)
        exposure = risk_engine.get_symbol_exposure(symbol)
        risk_exposure_ratio.labels(symbol=symbol).set(exposure / max_exposure)


def start_metrics_server():
    start_http_server(METRICS_PORT)
