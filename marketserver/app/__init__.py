import re

from flask import Flask, jsonify, Response, request

from app.config import Config
from app.model import HealthResponse, IndexResponse, BlobEntry, ErrorResponse
from shared.blob import get_store

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _list_blobs(store):
    filenames = store.list()
    body = IndexResponse(blobs=[BlobEntry(filename=f) for f in filenames])
    return jsonify(body.to_dict()), 200


def _get_blob(store, date):
    if not _DATE_RE.match(date):
        return jsonify(ErrorResponse(error="invalid date format").to_dict()), 400
    filename = f"decisions_{date}.jsonl"
    try:
        handle = store.read(filename)
        return Response(handle, mimetype="application/x-ndjson")
    except FileNotFoundError:
        return jsonify(ErrorResponse(error="not found").to_dict()), 404


def create_app(config=None):
    app = Flask(__name__)

    cfg = config or Config
    app.config.from_object(cfg)

    blob_store = get_store(cfg.BLOB_BACKEND, cfg.BLOB_STORE_PATH)
    trade_store = get_store(cfg.BLOB_BACKEND, cfg.TRADE_BLOB_STORE_PATH)

    @app.after_request
    def _cors(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    @app.route('/health', methods=["GET"])
    def health():
        return jsonify(HealthResponse().to_dict()), 200

    # --- Narrative blobs ---

    @app.route('/blobs', methods=["GET"])
    def list_blobs():
        return _list_blobs(blob_store)

    @app.route('/blobs/<date>', methods=["GET"])
    def get_blob(date):
        return _get_blob(blob_store, date)

    # --- Trade blobs ---

    @app.route('/trades', methods=["GET"])
    def list_trades():
        return _list_blobs(trade_store)

    @app.route('/trades/<date>', methods=["GET"])
    def get_trade(date):
        return _get_blob(trade_store, date)

    return app
