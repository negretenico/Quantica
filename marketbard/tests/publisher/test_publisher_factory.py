import pytest
from unittest.mock import MagicMock


def test_disk_backend_returns_local_blob_publisher(monkeypatch):
    monkeypatch.setattr("app.config.Config.PUBLISHER_BACKEND", "disk")
    monkeypatch.setattr("app.config.Config.BLOB_LOCAL_DIR", "/tmp/test-marketbard")

    from publisher.factory import build_publisher
    from publisher.local_blob_publisher import LocalBlobPublisher

    result = build_publisher()
    assert isinstance(result, LocalBlobPublisher)
    assert result.directory == "/tmp/test-marketbard"


def test_s3_backend_returns_s3_blob_publisher(monkeypatch):
    pytest.importorskip("boto3")
    monkeypatch.setattr("app.config.Config.PUBLISHER_BACKEND", "s3")
    monkeypatch.setattr("app.config.Config.S3_BUCKET", "my-bucket")
    monkeypatch.setattr("app.config.Config.S3_PREFIX", "news")
    monkeypatch.setattr("app.config.Config.S3_REGION", "us-east-1")
    monkeypatch.setattr("publisher.s3_blob_publisher.boto3.client", lambda *a, **kw: MagicMock())

    from publisher.factory import build_publisher
    from publisher.s3_blob_publisher import S3BlobPublisher

    result = build_publisher()
    assert isinstance(result, S3BlobPublisher)


def test_unknown_backend_falls_back_to_disk(monkeypatch):
    monkeypatch.setattr("app.config.Config.PUBLISHER_BACKEND", "ftp")
    monkeypatch.setattr("app.config.Config.BLOB_LOCAL_DIR", "/tmp/test-marketbard")

    from publisher.factory import build_publisher
    from publisher.local_blob_publisher import LocalBlobPublisher

    result = build_publisher()
    assert isinstance(result, LocalBlobPublisher)


def test_s3_backend_with_empty_bucket_raises_value_error(monkeypatch):
    monkeypatch.setattr("app.config.Config.PUBLISHER_BACKEND", "s3")
    monkeypatch.setattr("app.config.Config.S3_BUCKET", "")

    from publisher.factory import build_publisher

    with pytest.raises(ValueError, match="S3_BUCKET"):
        build_publisher()
