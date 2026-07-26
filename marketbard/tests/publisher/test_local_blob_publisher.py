import json
import os
import re
import tempfile

import pytest

from publisher.local_blob_publisher import LocalBlobPublisher


def _md_files(directory):
    return [f for f in os.listdir(directory) if f.endswith(".md")]


def test_creates_new_file_with_story_content():
    with tempfile.TemporaryDirectory() as tmp:
        publisher = LocalBlobPublisher(directory=tmp)
        publisher.publish("Today the market did something wild.")

        files = _md_files(tmp)
        assert len(files) == 1
        content = open(os.path.join(tmp, files[0]), encoding="utf-8").read()
        assert content == "Today the market did something wild."


def test_each_publish_creates_a_new_file():
    with tempfile.TemporaryDirectory() as tmp:
        publisher = LocalBlobPublisher(directory=tmp)
        publisher.publish("First story.")
        publisher.publish("Second story.")

        assert len(_md_files(tmp)) == 2


def test_filename_matches_timestamp_pattern():
    with tempfile.TemporaryDirectory() as tmp:
        publisher = LocalBlobPublisher(directory=tmp)
        publisher.publish("Story.")

        filename = _md_files(tmp)[0]
        assert re.match(r"^news_\d{8}_\d{6}_\d{6}\.md$", filename)


def test_creates_directory_if_missing():
    with tempfile.TemporaryDirectory() as tmp:
        target = os.path.join(tmp, "nested", "output")
        publisher = LocalBlobPublisher(directory=target)
        publisher.publish("Story.")

        assert os.path.isdir(target)
        assert len(_md_files(target)) == 1


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
        assert re.match(r"^news_\d{8}_\d{6}_\d{6}\.md$", entry["filename"])
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

        md_files = sorted(_md_files(tmp))
        first_filename = md_files[0]
        second_filename = md_files[1]

        filenames = [b["filename"] for b in blobs]
        assert filenames.index(second_filename) < filenames.index(first_filename)
