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
    ["type"],
)


def start_metrics_server(port: int = METRICS_PORT):
    start_http_server(port)
