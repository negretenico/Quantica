"""Tests for scripts/backtest/evaluate.py"""

import csv
import json
import os
import tempfile

import pytest

from scripts.backtest.evaluate import CSV_COLUMNS, sweep


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


# ---------------------------------------------------------------------------
# sweep()
# ---------------------------------------------------------------------------


def test_sweep_returns_row_per_threshold():
    trades = [_trade(quantity="500000.0") for _ in range(100)]
    rows = sweep(trades)
    # 7 large_trade + 7 price_spike + 7 dominant_side = 21
    assert len(rows) == 21


def test_sweep_row_keys_match_csv_columns():
    trades = [_trade() for _ in range(10)]
    rows = sweep(trades)
    for row in rows:
        assert set(row.keys()) == set(CSV_COLUMNS)


def test_sweep_fire_rate_zero_when_no_fires():
    # Quantity well below every large_trade threshold; flat price; alternating sides
    trades = []
    for i in range(100):
        side = "BUY" if i % 2 == 0 else "SELL"
        trades.append(_trade(quantity="1.0", price="100.00", side=side))

    rows = sweep(trades)
    large_trade_rows = [r for r in rows if r["detector"] == "large_trade"]
    for row in large_trade_rows:
        assert row["fire_count"] == 0
        assert row["fire_rate_per_1k_trades"] == 0.0


def test_sweep_fire_rate_calculation():
    # 1000 trades, all quantity=2_000_001 → fires for thresholds ≤ 2_000_000
    trades = [_trade(quantity="2000001.0") for _ in range(1_000)]
    rows = sweep(trades)
    # threshold=2_000_000 row: all 1000 trades fire → rate = 1000/1000*1000 = 1000.0
    row = next(r for r in rows if r["detector"] == "large_trade" and r["threshold"] == 2_000_000)
    assert row["fire_count"] == 1_000
    assert row["fire_rate_per_1k_trades"] == 1_000.0


def test_sweep_detector_names():
    trades = [_trade() for _ in range(10)]
    rows = sweep(trades)
    names = {r["detector"] for r in rows}
    assert names == {"large_trade", "price_spike", "dominant_side"}


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------


def test_cli_writes_csv(tmp_path):
    from scripts.backtest.evaluate import main

    # Write a minimal JSONL dump (10 trades)
    dump_file = tmp_path / "trades.jsonl"
    records = [
        {"s": "BTCUSDT", "p": "100.00", "q": "1.0", "m": False, "E": i}
        for i in range(10)
    ]
    dump_file.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

    out_dir = tmp_path / "results"
    main(["--dump-path", str(dump_file), "--output-dir", str(out_dir)])

    csv_path = out_dir / "threshold_sweep.csv"
    assert csv_path.exists()

    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    assert len(rows) == 21
    assert reader.fieldnames == CSV_COLUMNS


def test_cli_exits_on_empty_dump(tmp_path):
    from scripts.backtest.evaluate import main

    dump_file = tmp_path / "empty.jsonl"
    dump_file.write_text("", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main(["--dump-path", str(dump_file), "--output-dir", str(tmp_path)])

    assert exc_info.value.code == 1
