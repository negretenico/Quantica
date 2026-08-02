from app.config import Config


def test_config_has_required_fields():
    config = Config()
    assert isinstance(config.RABBITMQ_URL, str)
    assert isinstance(config.DISCORD_WEBHOOK_URL, str)
    assert isinstance(config.NOTIFY_EXCHANGE, str)
    assert isinstance(config.SIGNAL_EXCHANGE, str)
    assert isinstance(config.SIGNAL_QUEUE, str)
    assert isinstance(config.NOTIFY_QUEUE, str)
    assert isinstance(config.SYNTHESIS_HOUR, int)
    assert isinstance(config.HEALTH_DIGEST_INTERVAL_MINUTES, int)
    assert isinstance(config.PROMETHEUS_TARGETS, str)


def test_config_exchange_defaults():
    config = Config()
    assert config.NOTIFY_EXCHANGE == "notifications"
    assert config.SIGNAL_EXCHANGE == "signal"
    assert config.SIGNAL_QUEUE == "signal.notify"
    assert config.NOTIFY_QUEUE == "notifications.notify"


def test_prometheus_target_list():
    config = Config()
    targets = config.prometheus_target_list()
    assert isinstance(targets, list)
    assert len(targets) >= 1


def test_str_representation():
    config = Config()
    s = str(config)
    assert "RabbitMQ" in s
    assert "Discord Webhook" in s
