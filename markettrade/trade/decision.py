from datetime import datetime, timezone

from app.config import Config

_BUY_SIGNALS = {"DOMINANT_SIDE", "LARGE_TRADE"}
_SELL_SIGNALS = {"PRICE_SPIKE"}


def decide(event: dict, config: Config = None) -> dict:
    if config is None:
        config = Config()

    required = {"symbol", "type", "cluster_id", "anomaly_score", "price"}
    missing = required - event.keys()
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    anomaly_score = float(event["anomaly_score"])
    signal_type = event["type"]

    match (anomaly_score > config.ANOMALY_SCORE_THRESHOLD, signal_type):
        case (True, s) if s in _BUY_SIGNALS:
            action = "BUY"
        case (True, s) if s in _SELL_SIGNALS:
            action = "SELL"
        case _:
            action = "HOLD"

    return {
        "symbol": event["symbol"],
        "signal_type": signal_type,
        "cluster_id": event["cluster_id"],
        "anomaly_score": anomaly_score,
        "action": action,
        "entry_price": float(event["price"]),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
