from app.config import Config
from trade.decision import decide
from trade.models import SignalEvent


def _config(**overrides):
    cfg = Config()
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


def _event(**overrides):
    base = {
        "symbol": "BTCUSDT",
        "type": "LARGE_TRADE",
        "cluster_id": 2,
        "anomaly_score": 0.9,
        "price": "42000.00",
    }
    base.update(overrides)
    return SignalEvent(**base)


# --- BUY cases ---

def test_large_trade_high_anomaly_is_buy():
    result = decide(_event(type="LARGE_TRADE", anomaly_score=0.9))
    assert result["action"] == "BUY"


def test_dominant_side_high_anomaly_is_buy():
    result = decide(_event(type="DOMINANT_SIDE", anomaly_score=0.8))
    assert result["action"] == "BUY"


# --- SELL case ---

def test_price_spike_high_anomaly_is_sell():
    result = decide(_event(type="PRICE_SPIKE", anomaly_score=0.95))
    assert result["action"] == "SELL"


# --- HOLD cases ---

def test_low_anomaly_is_hold():
    result = decide(_event(type="LARGE_TRADE", anomaly_score=0.5))
    assert result["action"] == "HOLD"


def test_anomaly_at_threshold_is_hold():
    result = decide(_event(anomaly_score=0.7))
    assert result["action"] == "HOLD"


def test_unknown_signal_type_above_threshold_is_hold():
    result = decide(_event(type="UNKNOWN_TYPE", anomaly_score=0.99))
    assert result["action"] == "HOLD"


# --- Output shape ---

def test_output_contains_all_required_fields():
    result = decide(_event())
    for field in ("symbol", "signal_type", "cluster_id", "anomaly_score", "action", "entry_price", "timestamp_utc"):
        assert field in result


def test_output_values_mapped_correctly():
    result = decide(_event(symbol="ETHUSDT", type="PRICE_SPIKE", cluster_id=3, anomaly_score=0.85, price="3000.50"))
    assert result["symbol"] == "ETHUSDT"
    assert result["signal_type"] == "PRICE_SPIKE"
    assert result["cluster_id"] == 3
    assert result["anomaly_score"] == 0.85
    assert result["entry_price"] == 3000.50


# --- Configurable threshold ---

def test_custom_threshold_respected():
    cfg = _config(ANOMALY_SCORE_THRESHOLD=0.5)
    result = decide(_event(type="LARGE_TRADE", anomaly_score=0.6), config=cfg)
    assert result["action"] == "BUY"


def test_custom_threshold_hold_below():
    cfg = _config(ANOMALY_SCORE_THRESHOLD=0.8)
    result = decide(_event(type="LARGE_TRADE", anomaly_score=0.75), config=cfg)
    assert result["action"] == "HOLD"


# --- raw_quantity ---

def test_raw_quantity_from_event():
    result = decide(_event(quantity="150.5"))
    assert result["raw_quantity"] == 150.5


def test_raw_quantity_defaults_to_zero():
    result = decide(_event())
    assert result["raw_quantity"] == 0.0
