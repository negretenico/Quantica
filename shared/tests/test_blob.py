import json
import os
from datetime import datetime, timezone

import pytest

from shared.blob import get_store
from shared.blob.store_factory import get_store as get_store_direct


def _today_filename(store_path: str) -> str:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return os.path.join(store_path, f"decisions_{date_str}.jsonl")


def test_write_record_lands_in_correct_file(tmp_path):
    store = get_store("disk", str(tmp_path))
    record = {"symbol": "AAPL", "price": 150.0, "side": "BUY"}

    store.write(record)

    expected_file = _today_filename(str(tmp_path))
    assert os.path.exists(expected_file)
    with open(expected_file) as f:
        lines = f.readlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == record


def test_get_store_s3_raises_not_implemented(tmp_path):
    with pytest.raises(NotImplementedError):
        get_store_direct("s3", str(tmp_path))


def test_two_writes_produce_two_lines(tmp_path):
    store = get_store("disk", str(tmp_path))
    first = {"symbol": "AAPL", "price": 150.0}
    second = {"symbol": "MSFT", "price": 300.0}

    store.write(first)
    store.write(second)

    expected_file = _today_filename(str(tmp_path))
    with open(expected_file) as f:
        lines = f.readlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == first
    assert json.loads(lines[1]) == second


def test_list_returns_filenames_only(tmp_path):
    store = get_store("disk", str(tmp_path))
    store.write({"symbol": "BTC"})

    filenames = store.list()
    assert len(filenames) == 1
    assert filenames[0].startswith("decisions_")
    assert "/" not in filenames[0] and "\\" not in filenames[0]


def test_list_empty_store(tmp_path):
    store = get_store("disk", str(tmp_path))
    assert store.list() == []


def test_list_sorted_newest_first(tmp_path):
    for name in ["decisions_2026-07-25.jsonl", "decisions_2026-07-28.jsonl", "decisions_2026-07-26.jsonl"]:
        path = os.path.join(str(tmp_path), name)
        with open(path, "w") as f:
            f.write('{"a":1}\n')

    store = get_store("disk", str(tmp_path))
    filenames = store.list()
    assert filenames[0] == "decisions_2026-07-28.jsonl"
    assert filenames[-1] == "decisions_2026-07-25.jsonl"


def test_read_returns_content(tmp_path):
    store = get_store("disk", str(tmp_path))
    store.write({"symbol": "ETH", "price": 50.0})

    filenames = store.list()
    handle = store.read(filenames[0])
    content = handle.read()
    handle.close()
    record = json.loads(content.decode())
    assert record["symbol"] == "ETH"


def test_read_missing_file_raises(tmp_path):
    store = get_store("disk", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        store.read("decisions_2099-01-01.jsonl")
