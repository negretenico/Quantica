import pytest
from pydantic import ValidationError

from trade.models import SignalEvent


def _event(**overrides):
    base = {
        "symbol": "BTCUSDT",
        "type": "LARGE_TRADE",
        "price": "42000.00",
    }
    base.update(overrides)
    return base


# --- symbol ---

def test_missing_symbol_rejected():
    data = _event()
    del data["symbol"]
    with pytest.raises(ValidationError):
        SignalEvent(**data)


def test_empty_symbol_rejected():
    with pytest.raises(ValidationError):
        SignalEvent(**_event(symbol=""))


def test_whitespace_symbol_rejected():
    with pytest.raises(ValidationError):
        SignalEvent(**_event(symbol="   "))


def test_non_string_symbol_rejected():
    with pytest.raises(ValidationError):
        SignalEvent(**_event(symbol=123))


def test_valid_symbol_accepted():
    event = SignalEvent(**_event(symbol="BTCUSDT"))
    assert event.symbol == "BTCUSDT"


# --- type ---

def test_missing_type_rejected():
    data = _event()
    del data["type"]
    with pytest.raises(ValidationError):
        SignalEvent(**data)


def test_empty_type_rejected():
    with pytest.raises(ValidationError):
        SignalEvent(**_event(type=""))


def test_valid_type_accepted():
    event = SignalEvent(**_event(type="LARGE_TRADE"))
    assert event.type == "LARGE_TRADE"


# --- price ---

def test_missing_price_rejected():
    data = _event()
    del data["price"]
    with pytest.raises(ValidationError):
        SignalEvent(**data)


def test_non_numeric_price_rejected():
    with pytest.raises(ValidationError):
        SignalEvent(**_event(price="not_a_number"))


def test_zero_price_rejected():
    with pytest.raises(ValidationError):
        SignalEvent(**_event(price=0))


def test_negative_price_rejected():
    with pytest.raises(ValidationError):
        SignalEvent(**_event(price=-100))


def test_string_price_coerced():
    event = SignalEvent(**_event(price="42000.00"))
    assert event.price == 42000.0


def test_float_price_accepted():
    event = SignalEvent(**_event(price=42000.0))
    assert event.price == 42000.0


# --- anomaly_score (optional) ---

def test_missing_anomaly_score_defaults_to_none():
    event = SignalEvent(**_event())
    assert event.anomaly_score is None


def test_non_numeric_anomaly_score_rejected():
    with pytest.raises(ValidationError):
        SignalEvent(**_event(anomaly_score="abc"))


def test_anomaly_score_below_zero_rejected():
    with pytest.raises(ValidationError):
        SignalEvent(**_event(anomaly_score=-0.1))


def test_anomaly_score_above_one_rejected():
    with pytest.raises(ValidationError):
        SignalEvent(**_event(anomaly_score=1.1))


def test_anomaly_score_zero_boundary_accepted():
    event = SignalEvent(**_event(anomaly_score=0.0))
    assert event.anomaly_score == 0.0


def test_anomaly_score_one_boundary_accepted():
    event = SignalEvent(**_event(anomaly_score=1.0))
    assert event.anomaly_score == 1.0


def test_anomaly_score_mid_accepted():
    event = SignalEvent(**_event(anomaly_score=0.5))
    assert event.anomaly_score == 0.5


# --- quantity (optional) ---

def test_missing_quantity_defaults_to_zero():
    event = SignalEvent(**_event())
    assert event.quantity == 0


def test_non_numeric_quantity_rejected():
    with pytest.raises(ValidationError):
        SignalEvent(**_event(quantity="abc"))


def test_negative_quantity_rejected():
    with pytest.raises(ValidationError):
        SignalEvent(**_event(quantity=-1))


def test_zero_quantity_accepted():
    event = SignalEvent(**_event(quantity=0))
    assert event.quantity == 0


def test_string_quantity_coerced():
    event = SignalEvent(**_event(quantity="150.5"))
    assert event.quantity == 150.5


# --- cluster_id (optional) ---

def test_missing_cluster_id_defaults_to_none():
    event = SignalEvent(**_event())
    assert event.cluster_id is None


def test_non_int_cluster_id_rejected():
    with pytest.raises(ValidationError):
        SignalEvent(**_event(cluster_id="not_int"))


def test_string_cluster_id_coerced():
    event = SignalEvent(**_event(cluster_id="3"))
    assert event.cluster_id == 3


def test_int_cluster_id_accepted():
    event = SignalEvent(**_event(cluster_id=2))
    assert event.cluster_id == 2


# --- full valid event ---

def test_full_valid_event_accepted():
    event = SignalEvent(**_event())
    assert event.symbol == "BTCUSDT"
    assert event.type == "LARGE_TRADE"
    assert event.price == 42000.0
    assert event.anomaly_score is None
    assert event.cluster_id is None
    assert event.quantity == 0


def test_enriched_event_accepted():
    event = SignalEvent(**_event(anomaly_score=0.9, cluster_id=2))
    assert event.anomaly_score == 0.9
    assert event.cluster_id == 2
