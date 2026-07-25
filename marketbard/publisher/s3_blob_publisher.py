import logging
from datetime import datetime, timezone

import boto3

from publisher.blob_publisher import BlobPublisher

logger = logging.getLogger(__name__)


class S3BlobPublisher(BlobPublisher):
    def __init__(self, bucket: str, prefix: str = "news", region: str = "us-east-1"):
        """
        bucket: S3 bucket name
        prefix: key prefix for news update objects (e.g. "news" → "news/news_20260724_201241.md")
        region: AWS region
        """
        self.bucket = bucket
        self.prefix = prefix
        self.s3 = boto3.client("s3", region_name=region)

    def publish(self, story: str) -> None:
        """Write a new dated news update object to S3."""
        now = datetime.now(timezone.utc)
        filename = f"news_{now.strftime('%Y%m%d_%H%M%S_%f')}.md"
        key = f"{self.prefix}/{filename}" if self.prefix else filename
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=story.encode("utf-8"),
            ContentType="text/markdown",
            Metadata={
                "date": now.strftime("%Y-%m-%d"),
                "timestamp": now.isoformat(),
            },
        )
        logger.info(f"S3BlobPublisher: wrote s3://{self.bucket}/{key}")
