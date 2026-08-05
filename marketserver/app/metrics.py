from prometheus_flask_exporter import PrometheusMetrics

METRICS_PORT = 8000


def init_metrics(app):
    PrometheusMetrics(app, group_by="url_rule")


def start_metrics_server(app):
    metrics = app.extensions.get("prometheus-metrics")
    if metrics:
        metrics.start_http_server(METRICS_PORT)
