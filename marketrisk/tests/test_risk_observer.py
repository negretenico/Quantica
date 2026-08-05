import pytest

from marketrisk.risk.observer import NearLimitObserver


class TestNearLimitObserver:
    def test_fires_on_crossing_threshold(self):
        observer = NearLimitObserver(threshold_pct=0.80)
        alert = observer.check("BTCUSDT", 4100.0, 5000.0)
        assert alert is not None
        assert alert.symbol == "BTCUSDT"
        assert alert.current_exposure == 4100.0
        assert alert.max_exposure == 5000.0
        assert alert.ratio == pytest.approx(0.82)

    def test_does_not_fire_when_already_active(self):
        observer = NearLimitObserver(threshold_pct=0.80)
        observer.check("BTCUSDT", 4100.0, 5000.0)
        second = observer.check("BTCUSDT", 4500.0, 5000.0)
        assert second is None

    def test_no_alert_below_threshold(self):
        observer = NearLimitObserver(threshold_pct=0.80)
        alert = observer.check("BTCUSDT", 3000.0, 5000.0)
        assert alert is None

    def test_exact_threshold_fires(self):
        observer = NearLimitObserver(threshold_pct=0.80)
        alert = observer.check("BTCUSDT", 4000.0, 5000.0)
        assert alert is not None
        assert alert.ratio == pytest.approx(0.80)

    def test_clears_when_dropping_below(self):
        observer = NearLimitObserver(threshold_pct=0.80)
        observer.check("BTCUSDT", 4100.0, 5000.0)
        assert observer.is_near_limit("BTCUSDT") is True

        observer.check("BTCUSDT", 3000.0, 5000.0)
        assert observer.is_near_limit("BTCUSDT") is False

    def test_fires_again_after_clearing(self):
        observer = NearLimitObserver(threshold_pct=0.80)
        first = observer.check("BTCUSDT", 4100.0, 5000.0)
        assert first is not None

        observer.check("BTCUSDT", 3000.0, 5000.0)

        second = observer.check("BTCUSDT", 4200.0, 5000.0)
        assert second is not None
        assert second.ratio == pytest.approx(0.84)

    def test_multiple_symbols_independent(self):
        observer = NearLimitObserver(threshold_pct=0.80)
        btc = observer.check("BTCUSDT", 4500.0, 5000.0)
        eth = observer.check("ETHUSDT", 2000.0, 5000.0)
        assert btc is not None
        assert eth is None
        assert observer.active_symbols() == {"BTCUSDT"}

    def test_active_symbols_reflects_state(self):
        observer = NearLimitObserver(threshold_pct=0.80)
        observer.check("BTCUSDT", 4100.0, 5000.0)
        observer.check("ETHUSDT", 4500.0, 5000.0)
        assert observer.active_symbols() == {"BTCUSDT", "ETHUSDT"}

        observer.check("BTCUSDT", 3000.0, 5000.0)
        assert observer.active_symbols() == {"ETHUSDT"}

    def test_custom_threshold(self):
        observer = NearLimitObserver(threshold_pct=0.95)
        below = observer.check("BTCUSDT", 4600.0, 5000.0)
        assert below is None

        above = observer.check("BTCUSDT", 4800.0, 5000.0)
        assert above is not None
        assert above.ratio == pytest.approx(0.96)

    def test_zero_max_exposure_returns_none(self):
        observer = NearLimitObserver(threshold_pct=0.80)
        alert = observer.check("BTCUSDT", 100.0, 0.0)
        assert alert is None

    def test_is_near_limit_false_when_not_tracked(self):
        observer = NearLimitObserver(threshold_pct=0.80)
        assert observer.is_near_limit("BTCUSDT") is False
