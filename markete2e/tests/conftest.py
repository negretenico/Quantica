import pytest

from app.config import Config
from e2e.helpers import wait_for_kafka, wait_for_markettransformer, wait_for_rabbitmq

_config = Config()


@pytest.fixture(scope="session")
def kafka_bootstrap() -> str:
    return _config.KAFKA_BOOTSTRAP


@pytest.fixture(scope="session")
def rabbitmq_url() -> str:
    return _config.RABBITMQ_URL


@pytest.fixture(scope="session")
def ensure_kafka(kafka_bootstrap):
    """Session-scoped: blocks until Kafka is reachable."""
    wait_for_kafka(kafka_bootstrap, timeout_seconds=_config.KAFKA_TIMEOUT_SECONDS)


@pytest.fixture(scope="session")
def ensure_rabbitmq(rabbitmq_url):
    """Session-scoped: blocks until RabbitMQ is reachable."""
    wait_for_rabbitmq(rabbitmq_url, timeout_seconds=30)


@pytest.fixture(scope="session")
def ensure_markettransformer():
    """Session-scoped: blocks until markettransformer container reports healthy."""
    wait_for_markettransformer(timeout_seconds=60)


@pytest.fixture(scope="session")
def ensure_infra(ensure_kafka, ensure_rabbitmq, ensure_markettransformer):
    """Session-scoped: waits for Kafka, RabbitMQ, and markettransformer."""
    pass
