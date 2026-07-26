import logging
from collections import defaultdict
from typing import Callable

from app.config import Config
from publisher.blob_publisher import BlobPublisher
from publisher.local_blob_publisher import LocalBlobPublisher
from publisher.s3_blob_publisher import S3BlobPublisher

logger = logging.getLogger(__name__)


def _disk_builder() -> BlobPublisher:
    return LocalBlobPublisher(directory=Config.BLOB_LOCAL_DIR)


def _s3_builder() -> BlobPublisher:
    if not Config.S3_BUCKET:
        raise ValueError("PUBLISHER_BACKEND=s3 requires S3_BUCKET to be set")
    return S3BlobPublisher(
        bucket=Config.S3_BUCKET,
        prefix=Config.S3_PREFIX,
        region=Config.S3_REGION,
    )


_REGISTRY: defaultdict[str, Callable[[], BlobPublisher]] = defaultdict(
    lambda: _disk_builder,
    {
        "disk": _disk_builder,
        "s3": _s3_builder,
    },
)


def build_publisher() -> BlobPublisher:
    backend = Config.PUBLISHER_BACKEND.lower().strip()
    logger.info(f"publisher.factory: building publisher for backend='{backend}'")
    return _REGISTRY[backend]()
