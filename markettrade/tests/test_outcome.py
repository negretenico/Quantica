from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock

import pytest

from trade.outcome import DecisionLog, DecisionRecord


def _decision(**overrides) -> dict:
    base = {
        "symbol": "BTCUSDT",
        "action": "BUY",
        "entry_price": 50000.0,
        "anomaly_score": 0.85,
        "signal_type": "DOMINANT_SIDE",
        "cluster_id": 2,
        "timestamp_utc": "2026-08-03T12:00:00+00:00",
    }
    base.update(overrides)
    return base


class TestDecisionRecord:
    def test_from_decision_maps_all_fields(self):
        d = _decision()
        rec = DecisionRecord.from_decision(d)
        assert rec.symbol == "BTCUSDT"
        assert rec.action == "BUY"
        assert rec.entry_price == 50000.0
        assert rec.anomaly_score == 0.85
        assert rec.signal_type == "DOMINANT_SIDE"
        assert rec.cluster_id == 2
        assert rec.timestamp_utc == "2026-08-03T12:00:00+00:00"

    def test_from_decision_missing_field_raises(self):
        d = _decision()
        del d["symbol"]
        with pytest.raises(KeyError):
            DecisionRecord.from_decision(d)

    def test_to_dict_roundtrips(self):
        d = _decision()
        result = DecisionRecord.from_decision(d).to_dict()
        assert result == d

    def test_record_is_frozen(self):
        rec = DecisionRecord.from_decision(_decision())
        with pytest.raises(FrozenInstanceError):
            rec.symbol = "ETHUSDT"

    def test_extra_fields_ignored(self):
        d = _decision(risk_approved=True, sized_quantity=10.0)
        rec = DecisionRecord.from_decision(d)
        assert rec.symbol == "BTCUSDT"
        assert not hasattr(rec, "risk_approved")


class TestDecisionLog:
    def test_record_appends_to_deque(self):
        store = MagicMock()
        log = DecisionLog(store)
        log.record(_decision())
        assert len(log.recent()) == 1

    def test_record_writes_to_store(self):
        store = MagicMock()
        log = DecisionLog(store)
        d = _decision()
        log.record(d)
        store.write.assert_called_once()
        written = store.write.call_args[0][0]
        assert written["symbol"] == "BTCUSDT"
        assert written["action"] == "BUY"

    def test_bounded_deque_evicts_oldest(self):
        store = MagicMock()
        log = DecisionLog(store, max_size=3)
        for i in range(4):
            log.record(_decision(symbol=f"SYM{i}"))
        records = log.recent(10)
        assert len(records) == 3
        assert records[0].symbol == "SYM1"
        assert records[2].symbol == "SYM3"

    def test_recent_returns_last_n(self):
        store = MagicMock()
        log = DecisionLog(store)
        for i in range(5):
            log.record(_decision(symbol=f"SYM{i}"))
        records = log.recent(2)
        assert len(records) == 2
        assert records[0].symbol == "SYM3"
        assert records[1].symbol == "SYM4"

    def test_recent_returns_all_when_n_exceeds_size(self):
        store = MagicMock()
        log = DecisionLog(store)
        log.record(_decision())
        records = log.recent(100)
        assert len(records) == 1

    def test_record_propagates_store_error(self):
        store = MagicMock()
        store.write.side_effect = IOError("disk full")
        log = DecisionLog(store)
        with pytest.raises(IOError, match="disk full"):
            log.record(_decision())
        # Record should still be in memory despite store failure
        # (append happens before write)
        assert len(log.recent()) == 1
