from prometheus_client import Counter, Histogram, start_http_server

METRICS_PORT = 8000

mcp_requests_total = Counter(
    "marketmcp_requests_total",
    "MCP requests received",
    ["resource", "tool"],
)

mcp_request_seconds = Histogram(
    "marketmcp_request_seconds",
    "Time to handle an MCP request",
    ["resource", "tool"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

mcp_errors_total = Counter(
    "marketmcp_errors_total",
    "MCP request errors",
    ["tool"],
)

tool_requests_total = Counter(
    "marketmcp_tool_requests_total",
    "Tool invocations",
    ["tool"],
)

tool_latency_seconds = Histogram(
    "marketmcp_tool_latency_seconds",
    "Tool execution latency",
    ["tool"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

resource_requests_total = Counter(
    "marketmcp_resource_requests_total",
    "Resource read requests",
    ["resource"],
)

resource_latency_seconds = Histogram(
    "marketmcp_resource_latency_seconds",
    "Resource read latency",
    ["resource"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)


stream_events_received_total = Counter(
    "marketmcp_stream_events_received_total",
    "Events received from RabbitMQ",
    ["source"],
)

stream_events_deduplicated_total = Counter(
    "marketmcp_stream_events_deduplicated_total",
    "Duplicate events dropped",
    ["source"],
)

stream_events_rate_limited_total = Counter(
    "marketmcp_stream_events_rate_limited_total",
    "Events dropped by rate limiter",
    ["source"],
)


def start_metrics_server(port: int = METRICS_PORT):
    start_http_server(port)
