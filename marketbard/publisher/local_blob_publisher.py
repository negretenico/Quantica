import json
import logging
import os
from dataclasses import asdict
from datetime import datetime, timezone

from publisher.blob_publisher import BlobPublisher
from publisher.blob_entry import BlobEntry, make_entry
from shared.blob import get_store

logger = logging.getLogger(__name__)

_INDEX_FILENAME = "index.json"
_MAX_ENTRIES = 100


class LocalBlobPublisher(BlobPublisher):
    def __init__(self, directory: str):
        """
        directory: folder where news update files will be written
        """
        self.directory = directory
        self._store = get_store("disk", directory)

    def publish(self, story: str) -> None:
        """Append a story record to the daily NDJSON blob and update the index."""
        now = datetime.now(timezone.utc)
        record = {"content": story, "written_at": now.isoformat()}
        self._store.write(record)
        daily_filename = f"decisions_{now.strftime('%Y-%m-%d')}.jsonl"
        logger.info(f"LocalBlobPublisher: wrote story to {daily_filename}")
        self._update_index(make_entry(daily_filename))

    def _update_index(self, entry: BlobEntry) -> None:
        index_path = os.path.join(self.directory, _INDEX_FILENAME)
        tmp_path = index_path + ".tmp"

        existing = []
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                existing = json.load(f).get("blobs", [])

        blobs = [asdict(entry)] + existing
        blobs = blobs[:_MAX_ENTRIES]

        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump({"blobs": blobs}, f, indent=2)
        os.replace(tmp_path, index_path)
        logger.info(f"LocalBlobPublisher: updated index ({len(blobs)} entries)")
