from flask import Flask

from app import config
from app.kafka_client import KafkaClientManager

kafka_manager = KafkaClientManager(config=config.Config)


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)
    return app
