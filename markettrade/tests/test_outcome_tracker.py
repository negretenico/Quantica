import threading
from unittest.mock import MagicMock, patch

from trade.outcome_tracker import OutcomeRecord, OutcomeTracker


def _make_record(
    symbol="BTCUSDT",
    action="BUY",
    entry_price=100.0,
    outcome_price=105.0,
    pnl_pct=0.05,
    direction_correct=True,
    window_seconds=60,
    decision_time="2026-01-01T00:00:00+00:00",
    recorded_at="2026-01-01T00:01:00+00:00",
):
    return {
        "type": "price_lookback",
        "symbol": symbol,
        "action": action,
        "entry_price": entry_price,
        "decision_time": decision_time,
        "window_seconds": window_seconds,
        "outcome_price": outcome_price,
        "pnl_pct": pnl_pct,
        "direction_correct": direction_correct,
        "recorded_at": recorded_at,
        "price_source": "cache",
    }


def _mock_metrics():
    """Patch the three metrics imported lazily inside record_outcome."""
    return (
        patch("app.metrics.outcome_tracker_total", new_callable=MagicMock),
        patch("app.metrics.outcome_tracker_correctness", new_callable=MagicMock),
        patch("app.metrics.outcome_tracker_errors_total", new_callable=MagicMock),
    )


# --- OutcomeRecord ---


def test_outcome_record_from_lookback_dict():
    record = _make_record()
    outcome = OutcomeRecord.from_lookback(record)
    assert outcome.symbol == "BTCUSDT"
    assert outcome.action == "BUY"
    assert outcome.entry_price == 100.0
    assert outcome.outcome_price == 105.0
    assert outcome.pnl_pct == 0.05
    assert outcome.direction_correct is True
    assert outcome.window_seconds == 60


def test_outcome_record_is_frozen():
    outcome = OutcomeRecord.from_lookback(_make_record())
    try:
        outcome.symbol = "ETHUSDT"
        assert False, "Should have raised FrozenInstanceError"
    except AttributeError:
        pass


# --- Directional correctness ---


def test_buy_correct_when_price_went_up():
    record = _make_record(action="BUY", entry_price=100.0, outcome_price=105.0, pnl_pct=0.05, direction_correct=True)
    outcome = OutcomeRecord.from_lookback(record)
    assert outcome.direction_correct is True


def test_buy_incorrect_when_price_went_down():
    record = _make_record(action="BUY", entry_price=100.0, outcome_price=95.0, pnl_pct=-0.05, direction_correct=False)
    outcome = OutcomeRecord.from_lookback(record)
    assert outcome.direction_correct is False


def test_sell_correct_when_price_went_down():
    record = _make_record(action="SELL", entry_price=100.0, outcome_price=95.0, pnl_pct=0.05, direction_correct=True)
    outcome = OutcomeRecord.from_lookback(record)
    assert outcome.direction_correct is True


def test_sell_incorrect_when_price_went_up():
    record = _make_record(action="SELL", entry_price=100.0, outcome_price=105.0, pnl_pct=-0.05, direction_correct=False)
    outcome = OutcomeRecord.from_lookback(record)
    assert outcome.direction_correct is False


def test_flat_price_not_correct():
    record = _make_record(entry_price=100.0, outcome_price=100.0, pnl_pct=0.0, direction_correct=False)
    outcome = OutcomeRecord.from_lookback(record)
    assert outcome.direction_correct is False


# --- OutcomeTracker aggregation ---


def test_record_outcome_appends_to_tracker():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.record_outcome(_make_record())
        assert len(tracker.outcomes_for_symbol("BTCUSDT")) == 1


def test_correctness_rate_all_correct():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        for _ in range(3):
            tracker.record_outcome(_make_record(direction_correct=True, pnl_pct=0.01))
        assert tracker.correctness_rate() == 1.0


def test_correctness_rate_mixed():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.record_outcome(_make_record(direction_correct=True, pnl_pct=0.01))
        tracker.record_outcome(_make_record(direction_correct=True, pnl_pct=0.01))
        tracker.record_outcome(_make_record(direction_correct=False, pnl_pct=-0.01))
        tracker.record_outcome(_make_record(direction_correct=False, pnl_pct=-0.01))
        assert tracker.correctness_rate() == 0.5


def test_correctness_rate_none_when_empty():
    tracker = OutcomeTracker()
    assert tracker.correctness_rate() is None


def test_correctness_rate_filtered_by_symbol():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.record_outcome(_make_record(symbol="BTCUSDT", direction_correct=True, pnl_pct=0.01))
        tracker.record_outcome(_make_record(symbol="ETHUSDT", direction_correct=False, pnl_pct=-0.01))
        assert tracker.correctness_rate(symbol="BTCUSDT") == 1.0
        assert tracker.correctness_rate(symbol="ETHUSDT") == 0.0


def test_correctness_rate_filtered_by_window():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.record_outcome(_make_record(window_seconds=60, direction_correct=True, pnl_pct=0.01))
        tracker.record_outcome(_make_record(window_seconds=300, direction_correct=False, pnl_pct=-0.01))
        assert tracker.correctness_rate(window=60) == 1.0
        assert tracker.correctness_rate(window=300) == 0.0


def test_outcomes_for_symbol_filters():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.record_outcome(_make_record(symbol="BTCUSDT"))
        tracker.record_outcome(_make_record(symbol="ETHUSDT"))
        tracker.record_outcome(_make_record(symbol="BTCUSDT"))
        assert len(tracker.outcomes_for_symbol("BTCUSDT")) == 2
        assert len(tracker.outcomes_for_symbol("ETHUSDT")) == 1


def test_outcomes_for_window_filters():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.record_outcome(_make_record(window_seconds=60))
        tracker.record_outcome(_make_record(window_seconds=300))
        assert len(tracker.outcomes_for_window(60)) == 1
        assert len(tracker.outcomes_for_window(300)) == 1


def test_summary_structure():
    with _mock_metrics()[0], _mock_metrics()[1], _mock_metrics()[2]:
        tracker = OutcomeTracker()
        tracker.record_outcome(_make_record(window_seconds=60, action="BUY", direction_correct=True, pnl_pct=0.01))
        tracker.record_outcome(_make_record(window_seconds=300, action="SELL", direction_correct=False, pnl_pct=-0.01))

        summary = tracker.summary()
        assert summary["total"] == 2
        assert 0.0 <= summary["overall_correctness"] <= 1.0
        assert 60 in summary["by_window"]
        assert 300 in summary["by_window"]
        assert "BUY" in summary["by_action"]
        assert "SELL" in summary["by_action"]
        assert summary["by_window"][60]["rate"] == 1.0
        assert summary["by_window"][300]["rate"] == 0.0


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
        tracker.record_outcome(_make_record(symbol="A"))
        tracker.record_outcome(_make_record(symbol="B"))
        tracker.record_outcome(_make_record(symbol="C"))
        tracker.record_outcome(_make_record(symbol="D"))
        # Oldest (A) should be evicted
        assert len(tracker.outcomes_for_symbol("A")) == 0
        assert len(tracker.outcomes_for_symbol("D")) == 1


def test_record_outcome_handles_invalid_record():
    with _mock_metrics()[0], _mock_metrics()[1], \
         _mock_metrics()[2] as mock_err:
        tracker = OutcomeTracker()
        tracker.record_outcome({"bad": "data"})  # missing required keys
        assert tracker.correctness_rate() is None
        mock_err.inc.assert_called_once()


# --- PriceLookback callback integration ---


def test_outcome_callback_invoked_after_write():
    from trade.price_lookback import InMemoryPriceCache, LookbackTask, PriceLookback

    callback = MagicMock()
    cache = InMemoryPriceCache()
    cache.record("BTCUSDT", 1060.0, 50500.0)

    store = MagicMock()
    source = MagicMock()

    with patch("trade.price_lookback.PriceLookback._run_scheduler"):
        lookback = PriceLookback(
            windows=[60],
            price_source=source,
            cache=cache,
            outcome_store=store,
            outcome_callback=callback,
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
         patch("app.metrics.lookback_latency", new_callable=MagicMock), \
         patch("app.metrics.lookback_pnl", new_callable=MagicMock):
        lookback._execute_task(task)

    store.write.assert_called_once()
    callback.assert_called_once()
    record = callback.call_args[0][0]
    assert record["symbol"] == "BTCUSDT"
    assert record["direction_correct"] is True


def test_outcome_callback_error_does_not_crash_scheduler():
    from trade.price_lookback import InMemoryPriceCache, LookbackTask, PriceLookback

    callback = MagicMock(side_effect=RuntimeError("boom"))
    cache = InMemoryPriceCache()
    cache.record("BTCUSDT", 1060.0, 50500.0)

    store = MagicMock()
    source = MagicMock()

    with patch("trade.price_lookback.PriceLookback._run_scheduler"):
        lookback = PriceLookback(
            windows=[60],
            price_source=source,
            cache=cache,
            outcome_store=store,
            outcome_callback=callback,
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
         patch("app.metrics.lookback_latency", new_callable=MagicMock), \
         patch("app.metrics.lookback_pnl", new_callable=MagicMock):
        lookback._execute_task(task)  # should not raise

    store.write.assert_called_once()
    callback.assert_called_once()
