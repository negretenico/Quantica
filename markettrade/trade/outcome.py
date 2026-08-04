import logging
from collections import deque
from dataclasses import asdict, dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DecisionRecord:
    symbol: str
    action: str
    entry_price: float
    anomaly_score: float
    signal_type: str
    cluster_id: int
    timestamp_utc: str

    @classmethod
    def from_decision(cls, decision: dict) -> "DecisionRecord":
        return cls(
            symbol=decision["symbol"],
            action=decision["action"],
            entry_price=decision["entry_price"],
            anomaly_score=decision["anomaly_score"],
            signal_type=decision["signal_type"],
            cluster_id=decision["cluster_id"],
            timestamp_utc=decision["timestamp_utc"],
        )

    def to_dict(self) -> dict:
        return asdict(self)


class DecisionLog:
    def __init__(self, store, max_size: int = 1000):
        self._store = store
        self._records: deque[DecisionRecord] = deque(maxlen=max_size)

    def record(self, decision: dict) -> None:
        rec = DecisionRecord.from_decision(decision)
        self._records.append(rec)
        self._store.write(rec.to_dict())

    def recent(self, n: int = 10) -> list[DecisionRecord]:
        items = list(self._records)
        return items[-n:] if n < len(items) else items
