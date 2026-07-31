from app.config import Config


def test_config_defaults():
    config = Config()
    assert config.rabbitmq.QUEUE == "signal.trade"
    assert config.rabbitmq.SIGNAL_EXCHANGE == "signal"
    assert config.blob_store.PATH == "./decisions"
    assert config.blob_store.BACKEND == "disk"
    assert config.risk.MAX_TRADE_QUANTITY == 1000.0
    assert config.risk.MAX_SYMBOL_EXPOSURE == 5000.0
    assert config.risk.MAX_DRAWDOWN_PCT == 0.20
