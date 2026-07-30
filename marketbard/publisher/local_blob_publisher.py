import logging
from datetime import datetime, timezone

from publisher.blob_publisher import BlobPublisher
from shared.blob import get_store

logger = logging.getLogger(__name__)


class LocalBlobPublisher(BlobPublisher):
    def __init__(self, directory: str):
        """
        directory: folder where news update files will be written
        """
        self.directory = directory
        self._store = get_store("disk", directory)

    def publish(self, story: str) -> None:
        """Append a story record to the daily NDJSON blob."""
        now = datetime.now(timezone.utc)
        record = {"content": story, "written_at": now.isoformat()}
        self._store.write(record)
        daily_filename = f"decisions_{now.strftime('%Y-%m-%d')}.jsonl"
        logger.info(f"LocalBlobPublisher: wrote story to {daily_filename}")
