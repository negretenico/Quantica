import hashlib
import json
import os
import re
import time

from flask import Flask, jsonify, Response, request

from app.config import Config
from app.metrics import init_metrics
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
    init_metrics(app)

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

    # --- Portfolio ---

    portfolio_path = cfg.PORTFOLIO_STATE_PATH
    poll_interval = cfg.PORTFOLIO_POLL_INTERVAL

    def _read_portfolio():
        try:
            with open(portfolio_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def _portfolio_event_id(data: dict) -> str:
        """Deterministic event ID from portfolio content — lets clients detect duplicates."""
        raw = json.dumps(data, sort_keys=True)
        return hashlib.sha1(raw.encode()).hexdigest()[:12]

    def _format_sse(data: dict, event: str, event_id: str) -> str:
        return f"id: {event_id}\nevent: {event}\ndata: {json.dumps(data)}\n\n"

    @app.route('/portfolio', methods=["GET"])
    def get_portfolio():
        data = _read_portfolio()
        if data is None:
            return jsonify(ErrorResponse(error="portfolio state not found").to_dict()), 404
        return jsonify(data), 200

    @app.route('/portfolio/subscribe', methods=["GET"])
    def portfolio_subscribe():
        heartbeat_interval = 15.0
        retry_ms = int(poll_interval * 1000)
        last_event_id = request.headers.get("Last-Event-ID")

        def _generate():
            last_mtime = 0.0
            last_heartbeat = time.monotonic()
            sent_id = last_event_id

            # Always emit retry hint as the first frame.
            yield f"retry: {retry_ms}\n\n"

            while True:
                try:
                    mtime = os.path.getmtime(portfolio_path)
                except OSError:
                    time.sleep(poll_interval)
                    continue

                if mtime > last_mtime:
                    last_mtime = mtime
                    data = _read_portfolio()
                    if data is not None:
                        event_id = _portfolio_event_id(data)
                        # On first connect, send snapshot; on subsequent, send update.
                        # Skip if the client already has this exact state.
                        if event_id != sent_id:
                            event_type = "snapshot" if sent_id is None or sent_id == last_event_id else "update"
                            yield _format_sse(data, event_type, event_id)
                            sent_id = event_id
                            last_heartbeat = time.monotonic()

                now = time.monotonic()
                if now - last_heartbeat >= heartbeat_interval:
                    yield ": keepalive\n\n"
                    last_heartbeat = now
                time.sleep(poll_interval)

        return Response(_generate(), mimetype="text/event-stream",
                        headers={"Cache-Control": "no-cache",
                                 "X-Accel-Buffering": "no"})

    return app
