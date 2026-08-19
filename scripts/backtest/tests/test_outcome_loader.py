"""Tests for scripts/backtest/outcome_loader.py"""

import json

import pytest

from scripts.backtest.outcome_loader import load_outcomes


def _outcome(
    symbol: str = "BTCUSDT",
    action: str = "BUY",
    entry_price: float = 100.0,
    outcome_price: float = 105.0,
    pnl_pct: float = 0.05,
    direction_correct: bool = True,
    window_seconds: int = 60,
    decision_time: str = "2026-01-01T00:00:00+00:00",
    recorded_at: str = "2026-01-01T00:01:00+00:00",
    anomaly_score: float = 0.0,
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
        "anomaly_score": anomaly_score,
    }


def test_load_single_file(tmp_path):
    f = tmp_path / "decisions_2026-01-01.jsonl"
    f.write_text(json.dumps(_outcome()) + "\n", encoding="utf-8")

    results = list(load_outcomes(str(f)))
    assert len(results) == 1
    assert results[0]["symbol"] == "BTCUSDT"


def test_load_directory(tmp_path):
    for day in ("2026-01-01", "2026-01-02"):
        f = tmp_path / f"decisions_{day}.jsonl"
        f.write_text(json.dumps(_outcome()) + "\n", encoding="utf-8")

    results = list(load_outcomes(str(tmp_path)))
    assert len(results) == 2


def test_skips_malformed_json(tmp_path):
    f = tmp_path / "decisions_2026-01-01.jsonl"
    f.write_text("not json\n" + json.dumps(_outcome()) + "\n", encoding="utf-8")

    results = list(load_outcomes(str(f)))
    assert len(results) == 1


def test_skips_missing_fields(tmp_path):
    incomplete = {"symbol": "BTCUSDT", "action": "BUY"}
    f = tmp_path / "decisions_2026-01-01.jsonl"
    f.write_text(json.dumps(incomplete) + "\n" + json.dumps(_outcome()) + "\n", encoding="utf-8")

    results = list(load_outcomes(str(f)))
    assert len(results) == 1


def test_empty_directory_yields_nothing(tmp_path):
    results = list(load_outcomes(str(tmp_path)))
    assert results == []


def test_skips_blank_lines(tmp_path):
    f = tmp_path / "decisions_2026-01-01.jsonl"
    f.write_text("\n" + json.dumps(_outcome()) + "\n\n", encoding="utf-8")

    results = list(load_outcomes(str(f)))
    assert len(results) == 1
