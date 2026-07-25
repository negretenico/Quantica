import os
import re
import tempfile

import pytest

from publisher.local_blob_publisher import LocalBlobPublisher


def test_creates_new_file_with_story_content():
    with tempfile.TemporaryDirectory() as tmp:
        publisher = LocalBlobPublisher(directory=tmp)
        publisher.publish("Today the market did something wild.")

        files = os.listdir(tmp)
        assert len(files) == 1
        content = open(os.path.join(tmp, files[0]), encoding="utf-8").read()
        assert content == "Today the market did something wild."


def test_each_publish_creates_a_new_file():
    with tempfile.TemporaryDirectory() as tmp:
        publisher = LocalBlobPublisher(directory=tmp)
        publisher.publish("First story.")
        publisher.publish("Second story.")

        files = os.listdir(tmp)
        assert len(files) == 2


def test_filename_matches_timestamp_pattern():
    with tempfile.TemporaryDirectory() as tmp:
        publisher = LocalBlobPublisher(directory=tmp)
        publisher.publish("Story.")

        filename = os.listdir(tmp)[0]
        assert re.match(r"^news_\d{8}_\d{6}_\d{6}\.md$", filename)


def test_creates_directory_if_missing():
    with tempfile.TemporaryDirectory() as tmp:
        target = os.path.join(tmp, "nested", "output")
        publisher = LocalBlobPublisher(directory=target)
        publisher.publish("Story.")

        assert os.path.isdir(target)
        assert len(os.listdir(target)) == 1
