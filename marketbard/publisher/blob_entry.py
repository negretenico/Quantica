from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class BlobEntry:
    filename: str
    written_at: str
    symbol_count: int = 0
    anomaly_count: int = 0


def make_entry(filename: str) -> BlobEntry:
    written_at = datetime.now(timezone.utc).isoformat()
    return BlobEntry(filename=filename, written_at=written_at)
