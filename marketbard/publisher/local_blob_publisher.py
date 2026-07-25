import logging
import os
from datetime import datetime, timezone

from publisher.blob_publisher import BlobPublisher

logger = logging.getLogger(__name__)


class LocalBlobPublisher(BlobPublisher):
    def __init__(self, directory: str):
        """
        directory: folder where news update files will be written
        """
        self.directory = directory

    def publish(self, story: str) -> None:
        """Write a new dated news update file to the local directory."""
        os.makedirs(self.directory, exist_ok=True)
        now = datetime.now(timezone.utc)
        filename = f"news_{now.strftime('%Y%m%d_%H%M%S_%f')}.md"
        path = os.path.join(self.directory, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(story)
        logger.info(f"LocalBlobPublisher: wrote {path}")
