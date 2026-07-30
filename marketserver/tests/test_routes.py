import json
import os
from dataclasses import dataclass

import pytest

from app import create_app


@dataclass
class _TestConfig:
    DEBUG = False
    BLOB_BACKEND = "disk"
    BLOB_STORE_PATH = ""
    BLOB_SERVER_PORT = 5001


@pytest.fixture
def client(tmp_path):
    cfg = _TestConfig()
    cfg.BLOB_STORE_PATH = str(tmp_path)
    flask_app = create_app(config=cfg)
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def _write_blob(tmp_path, date, records):
    filename = f"decisions_{date}.jsonl"
    path = os.path.join(str(tmp_path), filename)
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


class TestHealth:
    def test_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.get_json() == {"status": "ok"}


class TestCors:
    def test_cors_header_present(self, client):
        resp = client.get("/health")
        assert resp.headers["Access-Control-Allow-Origin"] == "*"


class TestIndex:
    def test_empty_store(self, client):
        resp = client.get("/index.json")
        assert resp.status_code == 200
        assert resp.get_json() == {"blobs": []}

    def test_lists_blob_filenames(self, client, tmp_path):
        _write_blob(tmp_path, "2026-07-27", [{"a": 1}])
        _write_blob(tmp_path, "2026-07-28", [{"b": 2}])

        resp = client.get("/index.json")
        assert resp.status_code == 200
        data = resp.get_json()
        filenames = [b["filename"] for b in data["blobs"]]
        assert "decisions_2026-07-27.jsonl" in filenames
        assert "decisions_2026-07-28.jsonl" in filenames

    def test_sorted_newest_first(self, client, tmp_path):
        _write_blob(tmp_path, "2026-07-25", [{"a": 1}])
        _write_blob(tmp_path, "2026-07-28", [{"b": 2}])
        _write_blob(tmp_path, "2026-07-26", [{"c": 3}])

        resp = client.get("/index.json")
        filenames = [b["filename"] for b in resp.get_json()["blobs"]]
        assert filenames[0] == "decisions_2026-07-28.jsonl"
        assert filenames[-1] == "decisions_2026-07-25.jsonl"


class TestBlob:
    def test_returns_ndjson(self, client, tmp_path):
        records = [{"symbol": "BTC", "price": 100}, {"symbol": "ETH", "price": 50}]
        _write_blob(tmp_path, "2026-07-28", records)

        resp = client.get("/blobs/2026-07-28.jsonl")
        assert resp.status_code == 200
        assert "application/x-ndjson" in resp.content_type
        lines = resp.data.decode().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0]) == records[0]

    def test_404_when_missing(self, client):
        resp = client.get("/blobs/2099-01-01.jsonl")
        assert resp.status_code == 404

    def test_rejects_non_date_string(self, client):
        resp = client.get("/blobs/notadate.jsonl")
        assert resp.status_code == 400
