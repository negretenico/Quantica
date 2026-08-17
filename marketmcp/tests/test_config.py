import os
from unittest.mock import patch

from app.config import Config


class TestConfigDefaults:
    def test_default_marketserver_url(self):
        config = Config()
        assert config.MARKETSERVER_BASE_URL == "http://localhost:5001"

    def test_default_metrics_port(self):
        config = Config()
        assert config.METRICS_PORT == 8000

    def test_default_log_level(self):
        config = Config()
        assert config.LOG_LEVEL == "INFO"


class TestConfigFromEnv:
    @patch.dict(os.environ, {"MARKETSERVER_BASE_URL": "http://server:9999"})
    def test_marketserver_url_from_env(self):
        config = Config()
        assert config.MARKETSERVER_BASE_URL == "http://server:9999"

    @patch.dict(os.environ, {"METRICS_PORT": "9090"})
    def test_metrics_port_from_env(self):
        config = Config()
        assert config.METRICS_PORT == 9090

    @patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"})
    def test_log_level_from_env(self):
        config = Config()
        assert config.LOG_LEVEL == "DEBUG"


class TestConfigStr:
    def test_str_contains_all_fields(self):
        config = Config()
        output = str(config)
        assert "MarketServer" in output
        assert "Metrics Port" in output
        assert "Log Level" in output
