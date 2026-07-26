import re
from unittest.mock import MagicMock, patch

import pytest

boto3 = pytest.importorskip("boto3")
from publisher.s3_blob_publisher import S3BlobPublisher


@pytest.fixture
def mock_s3(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr("publisher.s3_blob_publisher.boto3.client", lambda *a, **kw: client)
    return client


def test_puts_story_content_to_s3(mock_s3):
    publisher = S3BlobPublisher(bucket="my-bucket", prefix="news")
    publisher.publish("Bitcoin went to the moon.")

    mock_s3.put_object.assert_called_once()
    call_kwargs = mock_s3.put_object.call_args.kwargs
    assert call_kwargs["Bucket"] == "my-bucket"
    assert call_kwargs["Body"] == b"Bitcoin went to the moon."
    assert call_kwargs["ContentType"] == "text/markdown"


def test_key_uses_prefix_and_timestamp_pattern(mock_s3):
    publisher = S3BlobPublisher(bucket="my-bucket", prefix="news")
    publisher.publish("Story.")

    key = mock_s3.put_object.call_args.kwargs["Key"]
    assert re.match(r"^news/news_\d{8}_\d{6}_\d{6}\.md$", key)


def test_key_without_prefix(mock_s3):
    publisher = S3BlobPublisher(bucket="my-bucket", prefix="")
    publisher.publish("Story.")

    key = mock_s3.put_object.call_args.kwargs["Key"]
    assert re.match(r"^news_\d{8}_\d{6}_\d{6}\.md$", key)


def test_s3_metadata_contains_date_and_timestamp(mock_s3):
    publisher = S3BlobPublisher(bucket="my-bucket", prefix="news")
    publisher.publish("Story.")

    metadata = mock_s3.put_object.call_args.kwargs["Metadata"]
    assert "date" in metadata
    assert "timestamp" in metadata
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", metadata["date"])


def test_each_publish_creates_a_new_s3_object(mock_s3):
    publisher = S3BlobPublisher(bucket="my-bucket", prefix="news")
    publisher.publish("First.")
    publisher.publish("Second.")

    assert mock_s3.put_object.call_count == 2
