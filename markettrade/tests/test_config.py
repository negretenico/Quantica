from app.config import Config


def test_config_defaults():
    config = Config()
    assert config.RABBITMQ_QUEUE == "signal.trade"
    assert config.SIGNAL_EXCHANGE == "signal"
    assert config.BLOB_STORE_PATH == "./decisions"
    assert config.BLOB_STORE_BACKEND == "disk"
