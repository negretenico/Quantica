import re

from flask import Flask, jsonify, Response

from app.config import Config
from shared.blob import get_store

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def create_app(config=None):
    app = Flask(__name__)

    cfg = config or Config
    app.config.from_object(cfg)

    blob_store = get_store(cfg.BLOB_BACKEND, cfg.BLOB_STORE_PATH)

    @app.after_request
    def _cors(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    @app.route('/health')
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route('/index.json')
    def index():
        filenames = blob_store.list()
        blobs = [{"filename": f} for f in filenames]
        return jsonify({"blobs": blobs}), 200

    @app.route('/blobs/<date>.jsonl')
    def blob(date):
        if not _DATE_RE.match(date):
            return jsonify({"error": "invalid date format"}), 400
        filename = f"decisions_{date}.jsonl"
        try:
            handle = blob_store.read(filename)
            return Response(handle, mimetype="application/x-ndjson")
        except FileNotFoundError:
            return jsonify({"error": "not found"}), 404

    return app
