"""Tests for scripts/backtest/recommend.py"""

import csv
import json

import pytest

from scripts.backtest.recommend import (
    CSV_COLUMNS,
    pick_recommendations,
    sweep_with_outcomes,
)


def _trade(
    symbol: str = "BTCUSDT",
    price: str = "100.00",
    quantity: str = "1.0",
    side: str = "BUY",
    event_time: int = 1_000,
) -> dict:
    return {
        "symbol": symbol,
        "price": price,
        "quantity": quantity,
        "side": side,
        "eventTime": event_time,
    }


def _outcome(
    symbol: str = "BTCUSDT",
    action: str = "BUY",
    entry_price: float = 100.0,
    outcome_price: float = 105.0,
    pnl_pct: float = 0.05,
    direction_correct: bool = True,
    window_seconds: int = 60,
    decision_time: str = "1970-01-01T00:00:01+00:00",
    recorded_at: str = "1970-01-01T00:01:01+00:00",
) -> dict:
    return {
        "symbol": symbol,
        "action": action,
        "entry_price": entry_price,
        "outcome_price": outcome_price,
        "pnl_pct": pnl_pct,
        "direction_correct": direction_correct,
        "window_seconds": window_seconds,
        "decision_time": decision_time,
        "recorded_at": recorded_at,
    }


# ---------------------------------------------------------------------------
# sweep_with_outcomes
# ---------------------------------------------------------------------------


def test_sweep_returns_row_per_threshold():
    trades = [_trade(quantity="500000.0") for _ in range(100)]
    rows = sweep_with_outcomes(trades, outcomes=[])
    # 7 large_trade + 7 price_spike + 7 dominant_side = 21
    assert len(rows) == 21


def test_sweep_row_keys_match_csv_columns():
    trades = [_trade() for _ in range(10)]
    rows = sweep_with_outcomes(trades, outcomes=[])
    for row in rows:
        assert set(row.keys()) == set(CSV_COLUMNS)


def test_sweep_with_no_outcomes_has_zero_stats():
    trades = [_trade(quantity="2000001.0") for _ in range(10)]
    rows = sweep_with_outcomes(trades, outcomes=[])
    for row in rows:
        assert row["outcome_count"] == 0
        assert row["correctness_rate"] == 0.0
        assert row["avg_pnl_pct"] == 0.0
        assert row["recommended"] is False


def test_sweep_matches_outcomes_to_signals():
    # Large trade fires for qty > 100_000. Create trades that fire at threshold=100_000.
    trades = [
        _trade(quantity="200000.0", side="BUY", event_time=1_000),
        _trade(quantity="200000.0", side="BUY", event_time=2_000),
        _trade(quantity="200000.0", side="BUY", event_time=3_000),
        _trade(quantity="200000.0", side="BUY", event_time=4_000),
    ]

    # Outcomes near those event times
    outcomes = [
        _outcome(direction_correct=True, pnl_pct=0.02, decision_time="1970-01-01T00:00:01+00:00"),
        _outcome(direction_correct=True, pnl_pct=0.03, decision_time="1970-01-01T00:00:02+00:00"),
        _outcome(direction_correct=False, pnl_pct=-0.01, decision_time="1970-01-01T00:00:03+00:00"),
        _outcome(direction_correct=True, pnl_pct=0.01, decision_time="1970-01-01T00:00:04+00:00"),
    ]

    rows = sweep_with_outcomes(trades, outcomes)
    lt_100k = next(r for r in rows if r["detector"] == "large_trade" and r["threshold"] == 100_000)

    assert lt_100k["fire_count"] == 4
    assert lt_100k["outcome_count"] == 4
    assert lt_100k["correctness_rate"] == 0.75


def test_sweep_filters_by_window():
    trades = [_trade(quantity="200000.0", event_time=1_000)]
    outcomes = [
        _outcome(window_seconds=60, decision_time="1970-01-01T00:00:01+00:00"),
        _outcome(window_seconds=300, decision_time="1970-01-01T00:00:01+00:00"),
    ]

    rows_60 = sweep_with_outcomes(trades, outcomes, window_seconds=60)
    lt_100k = next(r for r in rows_60 if r["detector"] == "large_trade" and r["threshold"] == 100_000)
    assert lt_100k["outcome_count"] == 1

    rows_300 = sweep_with_outcomes(trades, outcomes, window_seconds=300)
    lt_100k_300 = next(r for r in rows_300 if r["detector"] == "large_trade" and r["threshold"] == 100_000)
    assert lt_100k_300["outcome_count"] == 1


def test_sweep_no_match_when_outside_tolerance():
    trades = [_trade(quantity="200000.0", event_time=1_000)]
    # Outcome 10 seconds away from the signal
    outcomes = [_outcome(decision_time="1970-01-01T00:00:11+00:00")]

    rows = sweep_with_outcomes(trades, outcomes, tolerance_ms=5_000)
    lt_100k = next(r for r in rows if r["detector"] == "large_trade" and r["threshold"] == 100_000)
    assert lt_100k["outcome_count"] == 0


# ---------------------------------------------------------------------------
# pick_recommendations
# ---------------------------------------------------------------------------


def test_pick_recommendations_marks_best():
    rows = [
        {"detector": "large_trade", "threshold": 100_000, "outcome_count": 5, "correctness_rate": 0.8, "avg_pnl_pct": 0.02, "recommended": False},
        {"detector": "large_trade", "threshold": 250_000, "outcome_count": 5, "correctness_rate": 0.6, "avg_pnl_pct": 0.05, "recommended": False},
    ]

    pick_recommendations(rows)
    assert rows[0]["recommended"] is True
    assert rows[1]["recommended"] is False


def test_pick_recommendations_tiebreak_on_pnl():
    rows = [
        {"detector": "large_trade", "threshold": 100_000, "outcome_count": 5, "correctness_rate": 0.8, "avg_pnl_pct": 0.01, "recommended": False},
        {"detector": "large_trade", "threshold": 250_000, "outcome_count": 5, "correctness_rate": 0.8, "avg_pnl_pct": 0.05, "recommended": False},
    ]

    pick_recommendations(rows)
    assert rows[0]["recommended"] is False
    assert rows[1]["recommended"] is True


def test_pick_recommendations_skips_low_outcome_count():
    rows = [
        {"detector": "large_trade", "threshold": 100_000, "outcome_count": 1, "correctness_rate": 1.0, "avg_pnl_pct": 0.10, "recommended": False},
        {"detector": "large_trade", "threshold": 250_000, "outcome_count": 5, "correctness_rate": 0.6, "avg_pnl_pct": 0.02, "recommended": False},
    ]

    pick_recommendations(rows, min_outcomes=3)
    assert rows[0]["recommended"] is False
    assert rows[1]["recommended"] is True


def test_pick_recommendations_per_detector():
    rows = [
        {"detector": "large_trade", "threshold": 100_000, "outcome_count": 5, "correctness_rate": 0.9, "avg_pnl_pct": 0.02, "recommended": False},
        {"detector": "price_spike", "threshold": 0.02, "outcome_count": 5, "correctness_rate": 0.7, "avg_pnl_pct": 0.01, "recommended": False},
    ]

    pick_recommendations(rows)
    assert rows[0]["recommended"] is True
    assert rows[1]["recommended"] is True


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------


def test_cli_writes_csv(tmp_path):
    from scripts.backtest.recommend import main

    dump_file = tmp_path / "trades.jsonl"
    records = [
        {"s": "BTCUSDT", "p": "100.00", "q": "200000.0", "m": False, "E": i * 1_000}
        for i in range(10)
    ]
    dump_file.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

    outcome_file = tmp_path / "decisions_2026-01-01.jsonl"
    outcomes = [
        {
            "symbol": "BTCUSDT",
            "action": "BUY",
            "entry_price": 100.0,
            "outcome_price": 105.0,
            "pnl_pct": 0.05,
            "direction_correct": True,
            "window_seconds": 60,
            "decision_time": f"1970-01-01T00:00:0{i}+00:00",
            "recorded_at": "1970-01-01T00:01:00+00:00",
        }
        for i in range(5)
    ]
    outcome_file.write_text("\n".join(json.dumps(o) for o in outcomes), encoding="utf-8")

    out_dir = tmp_path / "results"
    main([
        "--dump-path", str(dump_file),
        "--outcome-path", str(outcome_file),
        "--output-dir", str(out_dir),
    ])

    csv_path = out_dir / "threshold_recommendations.csv"
    assert csv_path.exists()

    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    assert len(rows) == 21
    assert reader.fieldnames == CSV_COLUMNS


def test_cli_exits_on_empty_dump(tmp_path):
    from scripts.backtest.recommend import main

    dump_file = tmp_path / "empty.jsonl"
    dump_file.write_text("", encoding="utf-8")

    outcome_file = tmp_path / "decisions_2026-01-01.jsonl"
    outcome_file.write_text(json.dumps({
        "symbol": "BTCUSDT", "action": "BUY", "entry_price": 100.0,
        "outcome_price": 105.0, "pnl_pct": 0.05, "direction_correct": True,
        "window_seconds": 60, "decision_time": "1970-01-01T00:00:01+00:00",
        "recorded_at": "1970-01-01T00:01:00+00:00",
    }) + "\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main(["--dump-path", str(dump_file), "--outcome-path", str(outcome_file)])

    assert exc_info.value.code == 1


def test_cli_exits_on_empty_outcomes(tmp_path):
    from scripts.backtest.recommend import main

    dump_file = tmp_path / "trades.jsonl"
    records = [
        {"s": "BTCUSDT", "p": "100.00", "q": "1.0", "m": False, "E": 1000}
    ]
    dump_file.write_text(json.dumps(records[0]) + "\n", encoding="utf-8")

    outcome_file = tmp_path / "decisions_2026-01-01.jsonl"
    outcome_file.write_text("", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main([
            "--dump-path", str(dump_file),
            "--outcome-path", str(outcome_file),
        ])

    assert exc_info.value.code == 1
