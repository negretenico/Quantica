from flask import Flask
from app import config
from app.rabbit_client import RabbitClientManager

rabbit_manager = RabbitClientManager(config=config.Config)


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)
    return app
