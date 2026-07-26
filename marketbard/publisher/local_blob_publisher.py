import json
import logging
import os
from dataclasses import asdict
from datetime import datetime, timezone

from publisher.blob_publisher import BlobPublisher
from publisher.blob_entry import BlobEntry, make_entry

logger = logging.getLogger(__name__)

_INDEX_FILENAME = "index.json"
_MAX_ENTRIES = 100


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
        self._update_index(make_entry(filename, story))

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
