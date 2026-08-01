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
    TRADE_BLOB_STORE_PATH = ""
    BLOB_SERVER_PORT = 5001


@pytest.fixture
def client(tmp_path):
    cfg = _TestConfig()
    cfg.BLOB_STORE_PATH = str(tmp_path)
    cfg.TRADE_BLOB_STORE_PATH = str(tmp_path / "trades")
    os.makedirs(cfg.TRADE_BLOB_STORE_PATH, exist_ok=True)
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


class TestListBlobs:
    def test_empty_store(self, client):
        resp = client.get("/blobs")
        assert resp.status_code == 200
        assert resp.get_json() == {"blobs": []}

    def test_lists_blob_filenames(self, client, tmp_path):
        _write_blob(tmp_path, "2026-07-27", [{"a": 1}])
        _write_blob(tmp_path, "2026-07-28", [{"b": 2}])

        resp = client.get("/blobs")
        assert resp.status_code == 200
        data = resp.get_json()
        filenames = [b["filename"] for b in data["blobs"]]
        assert "decisions_2026-07-27.jsonl" in filenames
        assert "decisions_2026-07-28.jsonl" in filenames

    def test_sorted_newest_first(self, client, tmp_path):
        _write_blob(tmp_path, "2026-07-25", [{"a": 1}])
        _write_blob(tmp_path, "2026-07-28", [{"b": 2}])
        _write_blob(tmp_path, "2026-07-26", [{"c": 3}])

        resp = client.get("/blobs")
        filenames = [b["filename"] for b in resp.get_json()["blobs"]]
        assert filenames[0] == "decisions_2026-07-28.jsonl"
        assert filenames[-1] == "decisions_2026-07-25.jsonl"


class TestGetBlob:
    def test_returns_ndjson(self, client, tmp_path):
        records = [{"symbol": "BTC", "price": 100}, {"symbol": "ETH", "price": 50}]
        _write_blob(tmp_path, "2026-07-28", records)

        resp = client.get("/blobs/2026-07-28")
        assert resp.status_code == 200
        assert "application/x-ndjson" in resp.content_type
        lines = resp.data.decode().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0]) == records[0]

    def test_404_when_missing(self, client):
        resp = client.get("/blobs/2099-01-01")
        assert resp.status_code == 404

    def test_rejects_non_date_string(self, client):
        resp = client.get("/blobs/notadate")
        assert resp.status_code == 400


class TestBlobContract:
    """Verify marketserver faithfully serves the schema produced by marketbard."""

    FIXTURE_RECORDS = [
        {
            "content": "## BTC/USDT\nAggressive buying detected on the 1m chart.",
            "written_at": "2026-07-28T14:23:01+00:00",
        },
        {
            "content": "ETH showed anomalous cluster behavior at 14:30 UTC.",
            "written_at": "2026-07-28T14:30:55+00:00",
        },
    ]

    def test_serves_fixture_preserving_schema(self, client, tmp_path):
        _write_blob(tmp_path, "2026-07-28", self.FIXTURE_RECORDS)

        resp = client.get("/blobs/2026-07-28")
        assert resp.status_code == 200

        lines = resp.data.decode().strip().split("\n")
        assert len(lines) == len(self.FIXTURE_RECORDS)

        for line, expected in zip(lines, self.FIXTURE_RECORDS):
            record = json.loads(line)
            assert "content" in record, "record missing 'content' field"
            assert "written_at" in record, "record missing 'written_at' field"
            assert record["content"] == expected["content"]
            assert record["written_at"] == expected["written_at"]

    def test_fixture_records_have_iso_timestamps(self):
        from datetime import datetime

        for record in self.FIXTURE_RECORDS:
            parsed = datetime.fromisoformat(record["written_at"])
            assert parsed.tzinfo is not None, "written_at must be timezone-aware"


def _write_trade_blob(tmp_path, date, records):
    trade_dir = os.path.join(str(tmp_path), "trades")
    os.makedirs(trade_dir, exist_ok=True)
    path = os.path.join(trade_dir, f"decisions_{date}.jsonl")
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


class TestListTrades:
    def test_empty_trade_store(self, client):
        resp = client.get("/trades")
        assert resp.status_code == 200
        assert resp.get_json() == {"blobs": []}

    def test_lists_trade_blobs(self, client, tmp_path):
        _write_trade_blob(tmp_path, "2026-07-30", [{"symbol": "BTC"}])
        resp = client.get("/trades")
        assert resp.status_code == 200
        filenames = [b["filename"] for b in resp.get_json()["blobs"]]
        assert "decisions_2026-07-30.jsonl" in filenames


class TestGetTrade:
    FIXTURE_RECORDS = [
        {
            "symbol": "BTCUSDT",
            "signal_type": "LARGE_TRADE",
            "cluster_id": 1,
            "anomaly_score": 0.87,
            "action": "BUY",
            "entry_price": 103500.25,
            "raw_quantity": 0.5,
            "timestamp_utc": "2026-07-30T14:30:00+00:00",
            "risk_approved": True,
            "sized_quantity": 0.0012,
        },
    ]

    def test_returns_trade_ndjson(self, client, tmp_path):
        _write_trade_blob(tmp_path, "2026-07-30", self.FIXTURE_RECORDS)
        resp = client.get("/trades/2026-07-30")
        assert resp.status_code == 200
        assert "application/x-ndjson" in resp.content_type
        record = json.loads(resp.data.decode().strip())
        assert record["symbol"] == "BTCUSDT"
        assert record["action"] == "BUY"
        assert record["risk_approved"] is True

    def test_trade_404_when_missing(self, client):
        resp = client.get("/trades/2099-01-01")
        assert resp.status_code == 404

    def test_trade_rejects_non_date(self, client):
        resp = client.get("/trades/baddate")
        assert resp.status_code == 400
