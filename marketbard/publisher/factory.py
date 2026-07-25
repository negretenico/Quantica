import logging

from app.config import Config
from publisher.blob_publisher import BlobPublisher
from publisher.github_publisher import GithubPublisher
from publisher.local_blob_publisher import LocalBlobPublisher
from publisher.s3_blob_publisher import S3BlobPublisher

logger = logging.getLogger(__name__)

_SUPPORTED_BACKENDS = {"github", "disk", "s3"}


def build_publisher() -> BlobPublisher:
    backend = Config.PUBLISHER_BACKEND.lower().strip()
    logger.info(f"publisher.factory: building publisher for backend='{backend}'")

    if backend == "github":
        return GithubPublisher(
            token=Config.GH_TOKEN,
            repo_name=Config.GITHUB_REPO,
            branch=Config.GITHUB_BRANCH,
        )
    elif backend == "disk":
        return LocalBlobPublisher(directory=Config.BLOB_LOCAL_DIR)
    elif backend == "s3":
        if not Config.S3_BUCKET:
            raise ValueError("PUBLISHER_BACKEND=s3 requires S3_BUCKET to be set")
        return S3BlobPublisher(
            bucket=Config.S3_BUCKET,
            prefix=Config.S3_PREFIX,
            region=Config.S3_REGION,
        )
    else:
        raise ValueError(
            f"Unknown PUBLISHER_BACKEND='{backend}'. "
            f"Supported values: {', '.join(sorted(_SUPPORTED_BACKENDS))}"
        )
