import glob
import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_BLOB_PATTERN = "decisions_*.jsonl"


class DiskStore:
    def __init__(self, store_path: str):
        self._store_path = store_path

    def write(self, record: dict) -> None:
        os.makedirs(self._store_path, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        file_path = os.path.join(self._store_path, f"decisions_{date_str}.jsonl")
        with open(file_path, "a") as f:
            f.write(json.dumps(record) + "\n")
        logger.debug(f"Wrote record to {file_path}")

    def list(self) -> list[str]:
        """Return blob filenames (not full paths), sorted newest first."""
        pattern = os.path.join(self._store_path, _BLOB_PATTERN)
        paths = glob.glob(pattern)
        paths.sort(reverse=True)
        return [os.path.basename(p) for p in paths]

    def read(self, filename: str):
        """Return an open file handle for the given blob filename.

        Caller is responsible for closing the handle.
        Raises FileNotFoundError if the file does not exist.
        """
        path = os.path.join(self._store_path, filename)
        return open(path, "rb")
