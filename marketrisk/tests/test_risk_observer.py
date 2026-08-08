import pytest

from marketrisk.risk.models import ConcentrationState
from marketrisk.risk.observer import ConcentrationObserver, NearLimitObserver


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

    def test_active_alerts_returns_copy(self):
        observer = NearLimitObserver(threshold_pct=0.80)
        observer.check("BTCUSDT", 4100.0, 5000.0)
        alerts = observer.active_alerts()
        assert "BTCUSDT" in alerts
        assert alerts["BTCUSDT"].ratio == pytest.approx(0.82)
        alerts.clear()
        assert observer.is_near_limit("BTCUSDT") is True


class TestConcentrationObserver:
    def _make(self, threshold_pct=0.80, max_correlated=3):
        near_limit = NearLimitObserver(threshold_pct=threshold_pct)
        return ConcentrationObserver(near_limit, max_correlated=max_correlated), near_limit

    def _push_near_limit(self, observer, symbol, exposure=4100.0, max_exp=5000.0):
        """Push a symbol into near-limit state and return the result tuple."""
        return observer.check(symbol, exposure, max_exp)

    def test_starts_armed(self):
        obs, _ = self._make()
        assert obs.state == ConcentrationState.ARMED

    def test_no_alert_below_threshold(self):
        obs, _ = self._make(max_correlated=3)
        _, conc = self._push_near_limit(obs, "BTCUSDT")
        assert conc is None
        _, conc = self._push_near_limit(obs, "ETHUSDT")
        assert conc is None
        assert obs.state == ConcentrationState.ARMED

    def test_fires_when_reaching_threshold(self):
        obs, _ = self._make(max_correlated=3)
        self._push_near_limit(obs, "BTCUSDT")
        self._push_near_limit(obs, "ETHUSDT")
        _, conc = self._push_near_limit(obs, "SOLUSDT")
        assert conc is not None
        assert conc.count == 3
        assert conc.threshold == 3
        assert set(conc.near_limit_symbols) == {"BTCUSDT", "ETHUSDT", "SOLUSDT"}
        assert obs.state == ConcentrationState.FIRED

    def test_does_not_fire_again_while_fired(self):
        obs, _ = self._make(max_correlated=3)
        self._push_near_limit(obs, "BTCUSDT")
        self._push_near_limit(obs, "ETHUSDT")
        self._push_near_limit(obs, "SOLUSDT")
        _, conc = self._push_near_limit(obs, "XRPUSDT")
        assert conc is None
        assert obs.state == ConcentrationState.FIRED

    def test_disarms_when_dropping_below_threshold(self):
        obs, near_limit = self._make(max_correlated=3)
        self._push_near_limit(obs, "BTCUSDT")
        self._push_near_limit(obs, "ETHUSDT")
        self._push_near_limit(obs, "SOLUSDT")
        assert obs.state == ConcentrationState.FIRED
        obs.check("BTCUSDT", 1000.0, 5000.0)
        assert obs.state == ConcentrationState.DISARMED

    def test_re_arms_after_disarmed_and_still_below(self):
        obs, _ = self._make(max_correlated=3)
        self._push_near_limit(obs, "BTCUSDT")
        self._push_near_limit(obs, "ETHUSDT")
        self._push_near_limit(obs, "SOLUSDT")
        obs.check("BTCUSDT", 1000.0, 5000.0)
        assert obs.state == ConcentrationState.DISARMED
        obs.check("ETHUSDT", 4200.0, 5000.0)
        assert obs.state == ConcentrationState.ARMED

    def test_refires_after_disarm(self):
        obs, _ = self._make(max_correlated=3)
        self._push_near_limit(obs, "BTCUSDT")
        self._push_near_limit(obs, "ETHUSDT")
        _, first = self._push_near_limit(obs, "SOLUSDT")
        assert first is not None
        # drop BTCUSDT → DISARMED (2 active)
        obs.check("BTCUSDT", 1000.0, 5000.0)
        assert obs.state == ConcentrationState.DISARMED
        # re-check ETHUSDT still near-limit → ARMED (still 2 active)
        obs.check("ETHUSDT", 4200.0, 5000.0)
        assert obs.state == ConcentrationState.ARMED
        # ADAUSDT pushes to 3 → FIRED again
        _, second = self._push_near_limit(obs, "ADAUSDT")
        assert second is not None
        assert obs.state == ConcentrationState.FIRED

    def test_alert_contains_correct_ratios(self):
        obs, _ = self._make(max_correlated=2)
        self._push_near_limit(obs, "BTCUSDT", exposure=4100.0, max_exp=5000.0)
        _, conc = self._push_near_limit(obs, "ETHUSDT", exposure=4500.0, max_exp=5000.0)
        assert conc is not None
        assert conc.symbol_ratios["BTCUSDT"] == pytest.approx(0.82)
        assert conc.symbol_ratios["ETHUSDT"] == pytest.approx(0.90)

    def test_custom_threshold(self):
        obs, _ = self._make(max_correlated=2)
        self._push_near_limit(obs, "BTCUSDT")
        _, conc = self._push_near_limit(obs, "ETHUSDT")
        assert conc is not None
        assert obs.state == ConcentrationState.FIRED

    def test_returns_near_limit_alert_passthrough(self):
        obs, _ = self._make(max_correlated=3)
        near, conc = self._push_near_limit(obs, "BTCUSDT")
        assert near is not None
        assert near.symbol == "BTCUSDT"
        assert conc is None

    def test_single_symbol_never_fires(self):
        obs, _ = self._make(max_correlated=3)
        _, conc = self._push_near_limit(obs, "BTCUSDT", exposure=4999.0, max_exp=5000.0)
        assert conc is None
        assert obs.state == ConcentrationState.ARMED
