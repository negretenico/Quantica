import os
from dataclasses import dataclass

import pytest
from prometheus_client import REGISTRY, generate_latest

from app import create_app


@dataclass
class _TestConfig:
    DEBUG = False
    BLOB_BACKEND = "disk"
    BLOB_STORE_PATH = ""
    TRADE_BLOB_STORE_PATH = ""
    BLOB_SERVER_PORT = 5001


@pytest.fixture(scope="module")
def metrics_client(tmp_path_factory):
    """Single app instance for the entire module to avoid global registry collisions."""
    tmp = tmp_path_factory.mktemp("metrics")
    cfg = _TestConfig()
    cfg.BLOB_STORE_PATH = str(tmp)
    cfg.TRADE_BLOB_STORE_PATH = str(tmp / "trades")
    os.makedirs(cfg.TRADE_BLOB_STORE_PATH, exist_ok=True)
    flask_app = create_app(config=cfg)
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


class TestMetricsInstrumentation:
    """Verify prometheus-flask-exporter instruments requests automatically.

    Uses a module-scoped client to avoid prometheus_client global registry
    collisions from creating multiple PrometheusMetrics instances.
    """

    def test_request_counter_present(self, metrics_client):
        metrics_client.get("/health")
        output = generate_latest(REGISTRY).decode()
        assert 'flask_http_request_total{method="GET",status="200"}' in output

    def test_request_duration_histogram_present(self, metrics_client):
        metrics_client.get("/health")
        output = generate_latest(REGISTRY).decode()
        assert "flask_http_request_duration_seconds_count" in output

    def test_error_statuses_tracked(self, metrics_client):
        metrics_client.get("/blobs/2099-01-01")
        metrics_client.get("/blobs/notadate")
        output = generate_latest(REGISTRY).decode()
        assert 'status="404"' in output
        assert 'status="400"' in output

    def test_histogram_groups_by_url_rule(self, metrics_client):
        """Paths are grouped by Flask url_rule, not literal path."""
        metrics_client.get("/blobs/2099-01-01")
        output = generate_latest(REGISTRY).decode()
        assert 'url_rule="/blobs/<date>"' in output
        assert 'url_rule="/blobs/2099-01-01"' not in output
