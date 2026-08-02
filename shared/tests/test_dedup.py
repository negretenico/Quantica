from shared.dedup import DedupFilter


def _event(symbol="BTCUSDT", event_time="1234567890", event_type="LARGE_TRADE"):
    return {"symbol": symbol, "eventTime": event_time, "type": event_type}


class TestDedupFilter:
    def test_first_event_is_not_duplicate(self):
        f = DedupFilter()
        assert f.is_duplicate(_event()) is False

    def test_same_event_twice_is_duplicate(self):
        f = DedupFilter()
        f.is_duplicate(_event())
        assert f.is_duplicate(_event()) is True

    def test_different_symbol_is_not_duplicate(self):
        f = DedupFilter()
        f.is_duplicate(_event(symbol="BTCUSDT"))
        assert f.is_duplicate(_event(symbol="ETHUSDT")) is False

    def test_different_time_is_not_duplicate(self):
        f = DedupFilter()
        f.is_duplicate(_event(event_time="1"))
        assert f.is_duplicate(_event(event_time="2")) is False

    def test_different_type_is_not_duplicate(self):
        f = DedupFilter()
        f.is_duplicate(_event(event_type="LARGE_TRADE"))
        assert f.is_duplicate(_event(event_type="PRICE_SPIKE")) is False

    def test_eviction_at_maxlen(self):
        f = DedupFilter(maxlen=2)
        f.is_duplicate(_event(event_time="1"))
        f.is_duplicate(_event(event_time="2"))
        # inserting a third evicts the oldest ("1")
        f.is_duplicate(_event(event_time="3"))
        # "1" was evicted, so it's accepted again
        assert f.is_duplicate(_event(event_time="1")) is False
        # "3" is still in the set
        assert f.is_duplicate(_event(event_time="3")) is True

    def test_missing_fields_still_dedup(self):
        f = DedupFilter()
        bare = {}
        assert f.is_duplicate(bare) is False
        assert f.is_duplicate(bare) is True
