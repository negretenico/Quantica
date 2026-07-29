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
