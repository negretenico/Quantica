from datetime import datetime, timezone

from app.config import Config
from trade.models import SignalEvent

_BUY_SIGNALS = {"DOMINANT_SIDE", "LARGE_TRADE"}
_SELL_SIGNALS = {"PRICE_SPIKE"}


def decide(event: SignalEvent, config: Config = None) -> dict:
    if config is None:
        config = Config()

    match (event.anomaly_score > config.ANOMALY_SCORE_THRESHOLD, event.type):
        case (True, s) if s in _BUY_SIGNALS:
            action = "BUY"
        case (True, s) if s in _SELL_SIGNALS:
            action = "SELL"
        case _:
            action = "HOLD"

    return {
        "symbol": event.symbol,
        "signal_type": event.type,
        "cluster_id": event.cluster_id,
        "anomaly_score": event.anomaly_score,
        "action": action,
        "entry_price": event.price,
        "raw_quantity": event.quantity,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
