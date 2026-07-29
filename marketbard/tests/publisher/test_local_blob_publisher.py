import json
import os
import tempfile

import pytest

from publisher.local_blob_publisher import LocalBlobPublisher


def _jsonl_files(directory):
    return [f for f in os.listdir(directory) if f.endswith(".jsonl")]


def _read_lines(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_creates_daily_jsonl_with_story_content():
    with tempfile.TemporaryDirectory() as tmp:
        publisher = LocalBlobPublisher(directory=tmp)
        publisher.publish("Today the market did something wild.")

        files = _jsonl_files(tmp)
        assert len(files) == 1
        lines = _read_lines(os.path.join(tmp, files[0]))
        assert len(lines) == 1
        assert lines[0]["content"] == "Today the market did something wild."
        assert "written_at" in lines[0]


def test_two_publishes_append_to_same_daily_file():
    with tempfile.TemporaryDirectory() as tmp:
        publisher = LocalBlobPublisher(directory=tmp)
        publisher.publish("First story.")
        publisher.publish("Second story.")

        files = _jsonl_files(tmp)
        assert len(files) == 1
        lines = _read_lines(os.path.join(tmp, files[0]))
        assert len(lines) == 2
        assert lines[0]["content"] == "First story."
        assert lines[1]["content"] == "Second story."


def test_filename_is_daily_jsonl():
    with tempfile.TemporaryDirectory() as tmp:
        publisher = LocalBlobPublisher(directory=tmp)
        publisher.publish("Story.")

        files = _jsonl_files(tmp)
        assert len(files) == 1
        assert files[0].startswith("decisions_")
        assert files[0].endswith(".jsonl")


def test_creates_directory_if_missing():
    with tempfile.TemporaryDirectory() as tmp:
        target = os.path.join(tmp, "nested", "output")
        publisher = LocalBlobPublisher(directory=target)
        publisher.publish("Story.")

        assert os.path.isdir(target)
        assert len(_jsonl_files(target)) == 1


def test_index_json_created_after_publish():
    with tempfile.TemporaryDirectory() as tmp:
        publisher = LocalBlobPublisher(directory=tmp)
        publisher.publish("First story.")

        index_path = os.path.join(tmp, "index.json")
        assert os.path.exists(index_path)

        index = json.loads(open(index_path, encoding="utf-8").read())
        assert "blobs" in index
        assert len(index["blobs"]) == 1

        entry = index["blobs"][0]
        assert entry["filename"].startswith("decisions_")
        assert entry["filename"].endswith(".jsonl")
        assert "written_at" in entry
        assert entry["symbol_count"] == 0
        assert entry["anomaly_count"] == 0


def test_index_json_newest_first_across_two_writes():
    with tempfile.TemporaryDirectory() as tmp:
        publisher = LocalBlobPublisher(directory=tmp)
        publisher.publish("First story.")
        publisher.publish("Second story.")

        index = json.loads(open(os.path.join(tmp, "index.json"), encoding="utf-8").read())
        blobs = index["blobs"]
        assert len(blobs) == 2
        # index is prepended on each write — newest entry is first
        assert blobs[0]["written_at"] >= blobs[1]["written_at"]
