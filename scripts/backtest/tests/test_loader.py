"""Tests for scripts/backtest/loader.py"""

import json
import logging
import os
import tempfile

import pytest

from scripts.backtest.loader import load_dump

DUMP_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "dump", "order_20260723_1Hours.jsonl"
)
REQUIRED_KEYS = {"symbol", "price", "quantity", "side", "eventTime"}


class TestLoadDumpRealFile:
    def test_yields_records(self):
        records = list(load_dump(DUMP_FILE))
        assert len(records) > 0

    def test_required_keys_present(self):
        first = next(iter(load_dump(DUMP_FILE)))
        assert REQUIRED_KEYS.issubset(first.keys())

    def test_side_values_are_buy_or_sell(self):
        for record in load_dump(DUMP_FILE):
            assert record["side"] in ("BUY", "SELL")
            break  # one record is enough to verify mapping


class TestLoadDumpEdgeCases:
    def _write_jsonl(self, lines: list[str]) -> str:
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8")
        for line in lines:
            f.write(line + "\n")
        f.close()
        return f.name

    def test_skips_malformed_json(self, caplog):
        valid = json.dumps({"s": "BTCUSDT", "p": "100.0", "q": "1.0", "m": False, "E": 1000})
        path = self._write_jsonl(["not-json", valid])
        with caplog.at_level(logging.WARNING):
            records = list(load_dump(path))
        os.unlink(path)
        assert len(records) == 1
        assert any("JSON parse error" in m for m in caplog.messages)

    def test_skips_missing_required_fields(self, caplog):
        incomplete = json.dumps({"s": "BTCUSDT", "p": "100.0"})  # missing q, m, E
        valid = json.dumps({"s": "BTCUSDT", "p": "100.0", "q": "1.0", "m": False, "E": 1000})
        path = self._write_jsonl([incomplete, valid])
        with caplog.at_level(logging.WARNING):
            records = list(load_dump(path))
        os.unlink(path)
        assert len(records) == 1
        assert any("missing required fields" in m for m in caplog.messages)

    def test_side_mapping(self):
        buy_line = json.dumps({"s": "BTCUSDT", "p": "100.0", "q": "1.0", "m": False, "E": 1})
        sell_line = json.dumps({"s": "BTCUSDT", "p": "100.0", "q": "1.0", "m": True, "E": 2})
        path = self._write_jsonl([buy_line, sell_line])
        records = list(load_dump(path))
        os.unlink(path)
        assert records[0]["side"] == "BUY"
        assert records[1]["side"] == "SELL"

    def test_strips_ingested_at(self):
        line = json.dumps(
            {"s": "X", "p": "1", "q": "1", "m": False, "E": 1, "_ingested_at": 9999}
        )
        path = self._write_jsonl([line])
        record = next(iter(load_dump(path)))
        os.unlink(path)
        assert "_ingested_at" not in record

    def test_skips_blank_lines(self):
        valid = json.dumps({"s": "X", "p": "1", "q": "1", "m": False, "E": 1})
        path = self._write_jsonl(["", valid, ""])
        records = list(load_dump(path))
        os.unlink(path)
        assert len(records) == 1
