import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


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
