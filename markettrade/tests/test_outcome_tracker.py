from unittest.mock import MagicMock, patch

from trade.outcome_tracker import OutcomeTracker


def _make_raw_record(
    symbol="BTCUSDT",
    action="BUY",
    entry_price=100.0,
    outcome_price=105.0,
    window_seconds=60,
    decision_time="2026-01-01T00:00:00+00:00",
    recorded_at="2026-01-01T00:01:00+00:00",
):
    """Raw lookback record — no pnl_pct or direction_correct (that's OutcomeTracker's job)."""
    return {
        "type": "price_lookback",
        "symbol": symbol,
        "action": action,
        "entry_price": entry_price,
        "decision_time": decision_time,
        "window_seconds": window_seconds,
        "outcome_price": outcome_price,
        "recorded_at": recorded_at,
        "price_source": "cache",
    }


def _mock_metrics():
    return (
        patch("app.metrics.outcome_tracker_total", new_callable=MagicMock),
        patch("app.metrics.outcome_tracker_correctness", new_callable=MagicMock),
        patch("app.metrics.outcome_tracker_errors_total", new_callable=MagicMock),
    )


# --- Directional correctness (the core evaluation logic) ---


def test_buy_correct_when_price_went_up():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.evaluate(_make_raw_record(action="BUY", entry_price=100.0, outcome_price=105.0))
        outcomes = tracker.outcomes_for_symbol("BTCUSDT")
        assert len(outcomes) == 1
        assert outcomes[0].direction_correct is True
        assert outcomes[0].pnl_pct > 0


def test_buy_incorrect_when_price_went_down():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.evaluate(_make_raw_record(action="BUY", entry_price=100.0, outcome_price=95.0))
        outcomes = tracker.outcomes_for_symbol("BTCUSDT")
        assert outcomes[0].direction_correct is False
        assert outcomes[0].pnl_pct < 0


def test_sell_correct_when_price_went_down():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.evaluate(_make_raw_record(action="SELL", entry_price=100.0, outcome_price=95.0))
        outcomes = tracker.outcomes_for_symbol("BTCUSDT")
        assert outcomes[0].direction_correct is True
        assert outcomes[0].pnl_pct > 0


def test_sell_incorrect_when_price_went_up():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.evaluate(_make_raw_record(action="SELL", entry_price=100.0, outcome_price=105.0))
        outcomes = tracker.outcomes_for_symbol("BTCUSDT")
        assert outcomes[0].direction_correct is False
        assert outcomes[0].pnl_pct < 0


def test_flat_price_not_correct():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.evaluate(_make_raw_record(entry_price=100.0, outcome_price=100.0))
        outcomes = tracker.outcomes_for_symbol("BTCUSDT")
        assert outcomes[0].direction_correct is False
        assert outcomes[0].pnl_pct == 0.0


def test_pnl_calculation_buy():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.evaluate(_make_raw_record(action="BUY", entry_price=100.0, outcome_price=105.0))
        assert tracker.outcomes_for_symbol("BTCUSDT")[0].pnl_pct == 0.05


def test_pnl_calculation_sell():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.evaluate(_make_raw_record(action="SELL", entry_price=100.0, outcome_price=95.0))
        assert tracker.outcomes_for_symbol("BTCUSDT")[0].pnl_pct == 0.05


# --- OutcomeTracker aggregation ---


def test_evaluate_appends_to_tracker():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.evaluate(_make_raw_record())
        assert len(tracker.outcomes_for_symbol("BTCUSDT")) == 1


def test_correctness_rate_all_correct():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        for _ in range(3):
            tracker.evaluate(_make_raw_record(action="BUY", entry_price=100.0, outcome_price=105.0))
        assert tracker.correctness_rate() == 1.0


def test_correctness_rate_mixed():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.evaluate(_make_raw_record(action="BUY", entry_price=100.0, outcome_price=105.0))
        tracker.evaluate(_make_raw_record(action="BUY", entry_price=100.0, outcome_price=105.0))
        tracker.evaluate(_make_raw_record(action="BUY", entry_price=100.0, outcome_price=95.0))
        tracker.evaluate(_make_raw_record(action="BUY", entry_price=100.0, outcome_price=95.0))
        assert tracker.correctness_rate() == 0.5


def test_correctness_rate_none_when_empty():
    tracker = OutcomeTracker()
    assert tracker.correctness_rate() is None


def test_correctness_rate_filtered_by_symbol():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.evaluate(_make_raw_record(symbol="BTCUSDT", action="BUY", entry_price=100.0, outcome_price=105.0))
        tracker.evaluate(_make_raw_record(symbol="ETHUSDT", action="BUY", entry_price=100.0, outcome_price=95.0))
        assert tracker.correctness_rate(symbol="BTCUSDT") == 1.0
        assert tracker.correctness_rate(symbol="ETHUSDT") == 0.0


def test_correctness_rate_filtered_by_window():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.evaluate(_make_raw_record(window_seconds=60, action="BUY", entry_price=100.0, outcome_price=105.0))
        tracker.evaluate(_make_raw_record(window_seconds=300, action="BUY", entry_price=100.0, outcome_price=95.0))
        assert tracker.correctness_rate(window=60) == 1.0
        assert tracker.correctness_rate(window=300) == 0.0


def test_outcomes_for_symbol_filters():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.evaluate(_make_raw_record(symbol="BTCUSDT"))
        tracker.evaluate(_make_raw_record(symbol="ETHUSDT"))
        tracker.evaluate(_make_raw_record(symbol="BTCUSDT"))
        assert len(tracker.outcomes_for_symbol("BTCUSDT")) == 2
        assert len(tracker.outcomes_for_symbol("ETHUSDT")) == 1


def test_outcomes_for_window_filters():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.evaluate(_make_raw_record(window_seconds=60))
        tracker.evaluate(_make_raw_record(window_seconds=300))
        assert len(tracker.outcomes_for_window(60)) == 1
        assert len(tracker.outcomes_for_window(300)) == 1


def test_summary_structure():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.evaluate(_make_raw_record(window_seconds=60, action="BUY", entry_price=100.0, outcome_price=105.0))
        tracker.evaluate(_make_raw_record(window_seconds=300, action="SELL", entry_price=100.0, outcome_price=105.0))

        summary = tracker.summary()
        assert summary["total"] == 2
        assert 0.0 <= summary["overall_correctness"] <= 1.0
        assert 60 in summary["by_window"]
        assert 300 in summary["by_window"]
        assert "BUY" in summary["by_action"]
        assert "SELL" in summary["by_action"]
        assert summary["by_window"][60]["rate"] == 1.0   # BUY, price went up
        assert summary["by_window"][300]["rate"] == 0.0   # SELL, price went up


def test_summary_empty():
    tracker = OutcomeTracker()
    summary = tracker.summary()
    assert summary["total"] == 0
    assert summary["overall_correctness"] is None
    assert summary["by_window"] == {}
    assert summary["by_action"] == {}


def test_bounded_deque_evicts_oldest():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker(max_outcomes=3)
        tracker.evaluate(_make_raw_record(symbol="A"))
        tracker.evaluate(_make_raw_record(symbol="B"))
        tracker.evaluate(_make_raw_record(symbol="C"))
        tracker.evaluate(_make_raw_record(symbol="D"))
        assert len(tracker.outcomes_for_symbol("A")) == 0
        assert len(tracker.outcomes_for_symbol("D")) == 1


def test_evaluate_handles_invalid_record():
    with _mock_metrics()[0], _mock_metrics()[1], \
         _mock_metrics()[2] as mock_err:
        tracker = OutcomeTracker()
        tracker.evaluate({"bad": "data"})
        assert tracker.correctness_rate() is None
        mock_err.inc.assert_called_once()


# --- PriceLookback integration ---


def test_tracker_invoked_after_lookback_write():
    from trade.price_lookback import InMemoryPriceCache, LookbackTask, PriceLookback

    tracker = OutcomeTracker()
    cache = InMemoryPriceCache()
    cache.record("BTCUSDT", 1060.0, 50500.0)

    store = MagicMock()

    with patch("trade.price_lookback.PriceLookback._run_scheduler"):
        lookback = PriceLookback(
            windows=[60],
            price_source=MagicMock(),
            cache=cache,
            outcome_store=store,
            outcome_tracker=tracker,
        )

    task = LookbackTask(
        due_time=1060.0,
        symbol="BTCUSDT",
        action="BUY",
        entry_price=50000.0,
        decision_time=1000.0,
        window=60,
        anomaly_score=0.85,
    )

    with patch("app.metrics.lookback_completed_total", new_callable=MagicMock), \
         patch("app.metrics.lookback_latency", new_callable=MagicMock), \
         _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        lookback._execute_task(task)

    store.write.assert_called_once()
    # Tracker should have evaluated the outcome
    outcomes = tracker.outcomes_for_symbol("BTCUSDT")
    assert len(outcomes) == 1
    assert outcomes[0].direction_correct is True
    assert outcomes[0].entry_price == 50000.0
    assert outcomes[0].outcome_price == 50500.0
    assert outcomes[0].anomaly_score == 0.85


def test_tracker_error_does_not_crash_lookback():
    from trade.price_lookback import InMemoryPriceCache, LookbackTask, PriceLookback

    tracker = MagicMock()
    tracker.evaluate.side_effect = RuntimeError("boom")
    cache = InMemoryPriceCache()
    cache.record("BTCUSDT", 1060.0, 50500.0)

    store = MagicMock()

    with patch("trade.price_lookback.PriceLookback._run_scheduler"):
        lookback = PriceLookback(
            windows=[60],
            price_source=MagicMock(),
            cache=cache,
            outcome_store=store,
            outcome_tracker=tracker,
        )

    task = LookbackTask(
        due_time=1060.0,
        symbol="BTCUSDT",
        action="BUY",
        entry_price=50000.0,
        decision_time=1000.0,
        window=60,
    )

    with patch("app.metrics.lookback_completed_total", new_callable=MagicMock), \
         patch("app.metrics.lookback_latency", new_callable=MagicMock):
        lookback._execute_task(task)  # should not raise

    store.write.assert_called_once()
    tracker.evaluate.assert_called_once()
