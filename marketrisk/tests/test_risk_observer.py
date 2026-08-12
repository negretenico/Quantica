import pytest

from marketrisk.risk.models import (
    AccumulationAlert,
    AccumulationCleared,
    ConcentrationAlert,
    ConcentrationCleared,
    ConcentrationState,
    NearLimitAlert,
    NearLimitCleared,
)
from marketrisk.risk.observer import (
    AccumulationObserver,
    ConcentrationObserver,
    NearLimitObserver,
    RiskObserverPipeline,
)


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

        result = observer.check("BTCUSDT", 3000.0, 5000.0)
        assert observer.is_near_limit("BTCUSDT") is False
        assert isinstance(result, NearLimitCleared)
        assert result.symbol == "BTCUSDT"

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
        conc = ConcentrationObserver(near_limit, max_correlated=max_correlated)
        return conc, near_limit

    def _push_near_limit(self, near_limit, conc, symbol, exposure=4100.0, max_exp=5000.0):
        """Run near-limit check then concentration check, return concentration alert."""
        near_limit.check(symbol, exposure, max_exp)
        return conc.check(symbol, exposure, max_exp)

    def test_starts_armed(self):
        obs, _ = self._make()
        assert obs.state == ConcentrationState.ARMED

    def test_no_alert_below_threshold(self):
        obs, nl = self._make(max_correlated=3)
        assert self._push_near_limit(nl, obs, "BTCUSDT") is None
        assert self._push_near_limit(nl, obs, "ETHUSDT") is None
        assert obs.state == ConcentrationState.ARMED

    def test_fires_when_reaching_threshold(self):
        obs, nl = self._make(max_correlated=3)
        self._push_near_limit(nl, obs, "BTCUSDT")
        self._push_near_limit(nl, obs, "ETHUSDT")
        conc = self._push_near_limit(nl, obs, "SOLUSDT")
        assert conc is not None
        assert conc.count == 3
        assert conc.threshold == 3
        assert set(conc.near_limit_symbols) == {"BTCUSDT", "ETHUSDT", "SOLUSDT"}
        assert obs.state == ConcentrationState.FIRED

    def test_does_not_fire_again_while_fired(self):
        obs, nl = self._make(max_correlated=3)
        self._push_near_limit(nl, obs, "BTCUSDT")
        self._push_near_limit(nl, obs, "ETHUSDT")
        self._push_near_limit(nl, obs, "SOLUSDT")
        conc = self._push_near_limit(nl, obs, "XRPUSDT")
        assert conc is None
        assert obs.state == ConcentrationState.FIRED

    def test_disarms_when_dropping_below_threshold(self):
        obs, nl = self._make(max_correlated=3)
        self._push_near_limit(nl, obs, "BTCUSDT")
        self._push_near_limit(nl, obs, "ETHUSDT")
        self._push_near_limit(nl, obs, "SOLUSDT")
        assert obs.state == ConcentrationState.FIRED
        nl.check("BTCUSDT", 1000.0, 5000.0)
        result = obs.check("BTCUSDT", 1000.0, 5000.0)
        assert obs.state == ConcentrationState.DISARMED
        assert isinstance(result, ConcentrationCleared)
        assert result.remaining_count == 2
        assert result.threshold == 3

    def test_re_arms_after_disarmed_and_still_below(self):
        obs, nl = self._make(max_correlated=3)
        self._push_near_limit(nl, obs, "BTCUSDT")
        self._push_near_limit(nl, obs, "ETHUSDT")
        self._push_near_limit(nl, obs, "SOLUSDT")
        nl.check("BTCUSDT", 1000.0, 5000.0)
        obs.check("BTCUSDT", 1000.0, 5000.0)
        assert obs.state == ConcentrationState.DISARMED
        nl.check("ETHUSDT", 4200.0, 5000.0)
        obs.check("ETHUSDT", 4200.0, 5000.0)
        assert obs.state == ConcentrationState.ARMED

    def test_refires_after_disarm(self):
        obs, nl = self._make(max_correlated=3)
        self._push_near_limit(nl, obs, "BTCUSDT")
        self._push_near_limit(nl, obs, "ETHUSDT")
        first = self._push_near_limit(nl, obs, "SOLUSDT")
        assert first is not None
        # drop BTCUSDT → DISARMED (2 active)
        nl.check("BTCUSDT", 1000.0, 5000.0)
        obs.check("BTCUSDT", 1000.0, 5000.0)
        assert obs.state == ConcentrationState.DISARMED
        # re-check ETHUSDT still near-limit → ARMED (still 2 active)
        nl.check("ETHUSDT", 4200.0, 5000.0)
        obs.check("ETHUSDT", 4200.0, 5000.0)
        assert obs.state == ConcentrationState.ARMED
        # ADAUSDT pushes to 3 → FIRED again
        second = self._push_near_limit(nl, obs, "ADAUSDT")
        assert second is not None
        assert obs.state == ConcentrationState.FIRED

    def test_alert_contains_correct_ratios(self):
        obs, nl = self._make(max_correlated=2)
        self._push_near_limit(nl, obs, "BTCUSDT", exposure=4100.0, max_exp=5000.0)
        conc = self._push_near_limit(nl, obs, "ETHUSDT", exposure=4500.0, max_exp=5000.0)
        assert conc is not None
        assert conc.symbol_ratios["BTCUSDT"] == pytest.approx(0.82)
        assert conc.symbol_ratios["ETHUSDT"] == pytest.approx(0.90)

    def test_custom_threshold(self):
        obs, nl = self._make(max_correlated=2)
        self._push_near_limit(nl, obs, "BTCUSDT")
        conc = self._push_near_limit(nl, obs, "ETHUSDT")
        assert conc is not None
        assert obs.state == ConcentrationState.FIRED

    def test_single_symbol_never_fires(self):
        obs, nl = self._make(max_correlated=3)
        conc = self._push_near_limit(nl, obs, "BTCUSDT", exposure=4999.0, max_exp=5000.0)
        assert conc is None
        assert obs.state == ConcentrationState.ARMED


class TestAccumulationObserver:
    def _check(self, observer, symbol, action, approved=True):
        return observer.check(symbol, 0.0, 5000.0, action=action, approved=approved)

    def test_no_alert_below_threshold(self):
        obs = AccumulationObserver(threshold=10)
        for _ in range(9):
            assert self._check(obs, "BTCUSDT", "BUY") is None

    def test_fires_at_threshold(self):
        obs = AccumulationObserver(threshold=10)
        for _ in range(9):
            self._check(obs, "BTCUSDT", "BUY")
        result = self._check(obs, "BTCUSDT", "BUY")
        assert isinstance(result, AccumulationAlert)
        assert result.symbol == "BTCUSDT"
        assert result.direction == "BUY"
        assert result.consecutive_count == 10
        assert result.threshold == 10

    def test_fire_once(self):
        obs = AccumulationObserver(threshold=10)
        for _ in range(10):
            self._check(obs, "BTCUSDT", "BUY")
        assert self._check(obs, "BTCUSDT", "BUY") is None

    def test_direction_change_resets_and_clears(self):
        obs = AccumulationObserver(threshold=10)
        for _ in range(10):
            self._check(obs, "BTCUSDT", "BUY")
        result = self._check(obs, "BTCUSDT", "SELL")
        assert isinstance(result, AccumulationCleared)
        assert result.symbol == "BTCUSDT"
        assert result.previous_direction == "BUY"
        assert result.new_direction == "SELL"

    def test_direction_change_without_fired_returns_none(self):
        obs = AccumulationObserver(threshold=10)
        for _ in range(5):
            self._check(obs, "BTCUSDT", "BUY")
        assert self._check(obs, "BTCUSDT", "SELL") is None
        assert obs.get_count("BTCUSDT") == ("SELL", 1)

    def test_refires_after_reset(self):
        obs = AccumulationObserver(threshold=3)
        for _ in range(3):
            self._check(obs, "BTCUSDT", "BUY")
        # direction change resets counter to SELL=1
        self._check(obs, "BTCUSDT", "SELL")
        # SELL=2
        self._check(obs, "BTCUSDT", "SELL")
        # SELL=3 — fires
        result = self._check(obs, "BTCUSDT", "SELL")
        assert isinstance(result, AccumulationAlert)
        assert result.direction == "SELL"
        assert result.consecutive_count == 3

    def test_multiple_symbols_independent(self):
        obs = AccumulationObserver(threshold=3)
        for _ in range(3):
            self._check(obs, "BTCUSDT", "BUY")
        for _ in range(2):
            self._check(obs, "ETHUSDT", "BUY")
        assert obs.get_count("BTCUSDT") == ("BUY", 3)
        assert obs.get_count("ETHUSDT") == ("BUY", 2)

    def test_rejected_trades_ignored(self):
        obs = AccumulationObserver(threshold=3)
        for _ in range(5):
            assert self._check(obs, "BTCUSDT", "BUY", approved=False) is None
        assert obs.get_count("BTCUSDT") is None

    def test_no_action_returns_none(self):
        obs = AccumulationObserver(threshold=3)
        result = obs.check("BTCUSDT", 0.0, 5000.0)
        assert result is None

    def test_sell_accumulation(self):
        obs = AccumulationObserver(threshold=3)
        for _ in range(2):
            self._check(obs, "BTCUSDT", "SELL")
        result = self._check(obs, "BTCUSDT", "SELL")
        assert isinstance(result, AccumulationAlert)
        assert result.direction == "SELL"

    def test_alternating_directions_never_fire(self):
        obs = AccumulationObserver(threshold=3)
        for _ in range(20):
            assert self._check(obs, "BTCUSDT", "BUY") is None
            assert self._check(obs, "BTCUSDT", "SELL") is None

    def test_custom_threshold(self):
        obs = AccumulationObserver(threshold=2)
        self._check(obs, "BTCUSDT", "BUY")
        result = self._check(obs, "BTCUSDT", "BUY")
        assert isinstance(result, AccumulationAlert)
        assert result.consecutive_count == 2

    def test_get_count_unknown_symbol(self):
        obs = AccumulationObserver(threshold=10)
        assert obs.get_count("UNKNOWN") is None


class TestRiskObserverPipeline:
    def test_collects_alerts_from_all_observers(self):
        nl = NearLimitObserver(threshold_pct=0.80)
        conc = ConcentrationObserver(nl, max_correlated=2)
        pipeline = RiskObserverPipeline([nl, conc])

        # first symbol — only near-limit fires
        alerts = pipeline.check("BTCUSDT", 4100.0, 5000.0)
        assert len(alerts) == 1
        assert alerts[0].symbol == "BTCUSDT"

        # second symbol — both near-limit and concentration fire
        alerts = pipeline.check("ETHUSDT", 4500.0, 5000.0)
        assert len(alerts) == 2

    def test_returns_empty_when_no_alerts(self):
        nl = NearLimitObserver(threshold_pct=0.80)
        conc = ConcentrationObserver(nl, max_correlated=3)
        pipeline = RiskObserverPipeline([nl, conc])

        alerts = pipeline.check("BTCUSDT", 1000.0, 5000.0)
        assert alerts == []

    def test_ordering_matters(self):
        """NearLimitObserver must run before ConcentrationObserver."""
        nl = NearLimitObserver(threshold_pct=0.80)
        conc = ConcentrationObserver(nl, max_correlated=2)
        pipeline = RiskObserverPipeline([nl, conc])

        pipeline.check("BTCUSDT", 4100.0, 5000.0)
        results = pipeline.check("ETHUSDT", 4500.0, 5000.0)

        assert isinstance(results[0], NearLimitAlert)
        assert isinstance(results[1], ConcentrationAlert)

    def test_cleared_signals_flow_through(self):
        """Pipeline collects cleared signals alongside alerts."""
        nl = NearLimitObserver(threshold_pct=0.80)
        conc = ConcentrationObserver(nl, max_correlated=2)
        pipeline = RiskObserverPipeline([nl, conc])

        # fire both
        pipeline.check("BTCUSDT", 4100.0, 5000.0)
        pipeline.check("ETHUSDT", 4500.0, 5000.0)

        # drop BTCUSDT — near-limit cleared + concentration cleared
        results = pipeline.check("BTCUSDT", 1000.0, 5000.0)
        assert isinstance(results[0], NearLimitCleared)
        assert results[0].symbol == "BTCUSDT"
        assert isinstance(results[1], ConcentrationCleared)
        assert results[1].remaining_count == 1

    def test_kwargs_forwarded_to_accumulation_observer(self):
        nl = NearLimitObserver(threshold_pct=0.80)
        conc = ConcentrationObserver(nl, max_correlated=3)
        accum = AccumulationObserver(threshold=2)
        pipeline = RiskObserverPipeline([nl, conc, accum])

        pipeline.check("BTCUSDT", 1000.0, 5000.0, action="BUY", approved=True)
        results = pipeline.check("BTCUSDT", 1000.0, 5000.0, action="BUY", approved=True)
        assert any(isinstance(r, AccumulationAlert) for r in results)

    def test_existing_observers_unaffected_by_kwargs(self):
        nl = NearLimitObserver(threshold_pct=0.80)
        conc = ConcentrationObserver(nl, max_correlated=2)
        accum = AccumulationObserver(threshold=100)
        pipeline = RiskObserverPipeline([nl, conc, accum])

        alerts = pipeline.check("BTCUSDT", 4100.0, 5000.0, action="BUY", approved=True)
        assert len(alerts) == 1
        assert isinstance(alerts[0], NearLimitAlert)
