from flask import Flask, jsonify
from app import config
from app.rabbit_client import RabbitClientManager

rabbit_manager = RabbitClientManager(config=config.Config)


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    @app.route('/health')
    def health():
        return jsonify({"status": "ok"}), 200

    return app
