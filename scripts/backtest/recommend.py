"""
recommend.py — Automated backtest threshold sweep with outcome data.

Correlates detector signals (from a trade dump) with real outcome records
(from markettrade's OutcomeWriter) to produce accuracy-enriched threshold
recommendations.

Usage::

    py scripts/backtest/recommend.py \\
        --dump-path dump/trades.jsonl \\
        --outcome-path decisions/trade/

    py scripts/backtest/recommend.py \\
        --dump-path dump/trades.jsonl \\
        --outcome-path decisions/trade/ \\
        --output-dir results/ \\
        --window 60

Output: <output-dir>/threshold_recommendations.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from scripts.backtest.detectors import dominant_side, large_trade, price_spike
from scripts.backtest.evaluate import (
    _DOMINANT_SIDE_STREAKS,
    _LARGE_TRADE_THRESHOLDS,
    _PRICE_SPIKE_PCTS,
)
from scripts.backtest.loader import load_dump
from scripts.backtest.outcome_loader import load_outcomes

log = logging.getLogger(__name__)

# Signal type → implied action for outcome matching.
_SIGNAL_TYPE_TO_ACTION: dict[str, str] = {
    "LARGE_TRADE": "BUY",
    "PRICE_SPIKE": "BUY",
    "DOMINANT_SIDE": "BUY",
}

CSV_COLUMNS = [
    "detector",
    "threshold",
    "fire_count",
    "fire_rate_per_1k_trades",
    "outcome_count",
    "correctness_rate",
    "avg_pnl_pct",
    "recommended",
]


def _parse_decision_time(dt_str: str) -> float:
    """Parse an ISO-8601 timestamp to epoch milliseconds."""
    dt = datetime.fromisoformat(dt_str)
    return dt.timestamp() * 1_000


def _build_outcome_index(
    outcomes: list[dict],
    window_seconds: int | None,
) -> dict[str, list[dict]]:
    """Index outcomes by symbol for fast lookup.

    Args:
        outcomes: Raw outcome dicts from ``outcome_loader.load_outcomes``.
        window_seconds: If set, only include outcomes with this window.

    Returns:
        Dict mapping symbol → list of outcome dicts, sorted by decision_time.
    """
    index: dict[str, list[dict]] = {}
    for o in outcomes:
        if window_seconds is not None and o["window_seconds"] != window_seconds:
            continue
        sym = o["symbol"]
        index.setdefault(sym, []).append(o)

    for lst in index.values():
        lst.sort(key=lambda o: o["decision_time"])

    return index


def _match_signal_to_outcome(
    signal: dict,
    outcome_index: dict[str, list[dict]],
    tolerance_ms: float = 5_000,
) -> dict | None:
    """Find the closest outcome record for a signal within *tolerance_ms*.

    Matches on symbol and uses the signal's side as the expected action.
    """
    symbol = signal["symbol"]
    candidates = outcome_index.get(symbol)
    if not candidates:
        return None

    signal_time = signal["eventTime"]
    signal_action = signal["side"]

    best: dict | None = None
    best_delta = float("inf")

    for o in candidates:
        if o["action"] != signal_action:
            continue
        try:
            o_time = _parse_decision_time(o["decision_time"])
        except (ValueError, TypeError):
            continue

        delta = abs(signal_time - o_time)
        if delta < best_delta and delta <= tolerance_ms:
            best_delta = delta
            best = o

    return best


def _evaluate_detector(
    signals: list[dict],
    outcome_index: dict[str, list[dict]],
    tolerance_ms: float,
) -> dict:
    """Compute outcome stats for a list of signals.

    Returns:
        Dict with ``outcome_count``, ``correctness_rate``, ``avg_pnl_pct``.
    """
    matched = 0
    correct = 0
    total_pnl = 0.0

    for sig in signals:
        outcome = _match_signal_to_outcome(sig, outcome_index, tolerance_ms)
        if outcome is None:
            continue
        matched += 1
        if outcome["direction_correct"]:
            correct += 1
        total_pnl += outcome["pnl_pct"]

    return {
        "outcome_count": matched,
        "correctness_rate": round(correct / matched, 4) if matched else 0.0,
        "avg_pnl_pct": round(total_pnl / matched, 6) if matched else 0.0,
    }


def sweep_with_outcomes(
    trades: list[dict],
    outcomes: list[dict],
    window_seconds: int | None = None,
    tolerance_ms: float = 5_000,
) -> list[dict]:
    """Run the threshold sweep and enrich each row with outcome metrics.

    Args:
        trades: Pre-loaded trade dicts from ``loader.load_dump``.
        outcomes: Pre-loaded outcome dicts from ``outcome_loader.load_outcomes``.
        window_seconds: Filter outcomes to this lookback window (seconds).
        tolerance_ms: Max time gap (ms) for signal↔outcome matching.

    Returns:
        List of result dicts with keys matching ``CSV_COLUMNS``.
        The ``recommended`` column is filled in by ``pick_recommendations``.
    """
    total = len(trades)
    outcome_index = _build_outcome_index(outcomes, window_seconds)

    rows: list[dict] = []

    for threshold in _LARGE_TRADE_THRESHOLDS:
        signals = large_trade(trades, threshold=threshold)
        fire_count = len(signals)
        stats = _evaluate_detector(signals, outcome_index, tolerance_ms)
        rows.append(
            {
                "detector": "large_trade",
                "threshold": threshold,
                "fire_count": fire_count,
                "fire_rate_per_1k_trades": round(fire_count / total * 1_000, 4) if total else 0.0,
                "recommended": False,
                **stats,
            }
        )

    for pct in _PRICE_SPIKE_PCTS:
        signals = price_spike(trades, pct=pct)
        fire_count = len(signals)
        stats = _evaluate_detector(signals, outcome_index, tolerance_ms)
        rows.append(
            {
                "detector": "price_spike",
                "threshold": pct,
                "fire_count": fire_count,
                "fire_rate_per_1k_trades": round(fire_count / total * 1_000, 4) if total else 0.0,
                "recommended": False,
                **stats,
            }
        )

    for streak in _DOMINANT_SIDE_STREAKS:
        signals = dominant_side(trades, streak=streak)
        fire_count = len(signals)
        stats = _evaluate_detector(signals, outcome_index, tolerance_ms)
        rows.append(
            {
                "detector": "dominant_side",
                "threshold": streak,
                "fire_count": fire_count,
                "fire_rate_per_1k_trades": round(fire_count / total * 1_000, 4) if total else 0.0,
                "recommended": False,
                **stats,
            }
        )

    return pick_recommendations(rows)


def pick_recommendations(
    rows: list[dict],
    min_outcomes: int = 3,
) -> list[dict]:
    """Mark the best threshold per detector as ``recommended=True``.

    Selection criteria (in priority order):
    1. Must have at least *min_outcomes* matched outcomes.
    2. Highest ``correctness_rate``.
    3. Tie-break: highest ``avg_pnl_pct``.

    Args:
        rows: Sweep result rows (mutated in-place).
        min_outcomes: Minimum outcome matches to be eligible.

    Returns:
        The same *rows* list with ``recommended`` flags set.
    """
    detectors = {r["detector"] for r in rows}
    for det in detectors:
        candidates = [
            r for r in rows
            if r["detector"] == det and r["outcome_count"] >= min_outcomes
        ]
        if not candidates:
            continue

        best = max(
            candidates,
            key=lambda r: (r["correctness_rate"], r["avg_pnl_pct"]),
        )
        best["recommended"] = True

    return rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Threshold sweep enriched with outcome data. "
            "Outputs threshold_recommendations.csv with accuracy metrics "
            "and recommended thresholds per detector."
        ),
    )
    parser.add_argument(
        "--dump-path",
        required=True,
        help="Path to a JSONL dump file produced by dump_topic.py.",
    )
    parser.add_argument(
        "--outcome-path",
        required=True,
        help=(
            "Path to a decisions_*.jsonl file or a directory containing them "
            "(as written by markettrade's OutcomeWriter)."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(os.path.dirname(__file__), "results"),
        help="Directory to write threshold_recommendations.csv (default: scripts/backtest/results/).",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=None,
        help="Filter outcomes to this lookback window in seconds (e.g. 60, 300). Default: all windows.",
    )
    parser.add_argument(
        "--tolerance-ms",
        type=float,
        default=5_000,
        help="Max time gap in milliseconds for signal↔outcome matching (default: 5000).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args(argv)

    log.info("Loading dump: %s", args.dump_path)
    trades = list(load_dump(args.dump_path))
    log.info("Loaded %d trades", len(trades))

    if not trades:
        log.error("No trades loaded — check dump path and file contents.")
        sys.exit(1)

    log.info("Loading outcomes: %s", args.outcome_path)
    outcomes = list(load_outcomes(args.outcome_path))
    log.info("Loaded %d outcome records", len(outcomes))

    if not outcomes:
        log.error("No outcome records loaded — check outcome path.")
        sys.exit(1)

    rows = sweep_with_outcomes(
        trades,
        outcomes,
        window_seconds=args.window,
        tolerance_ms=args.tolerance_ms,
    )

    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, "threshold_recommendations.csv")

    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    recommended = [r for r in rows if r["recommended"]]
    log.info("Wrote %d rows → %s", len(rows), out_path)
    for rec in recommended:
        log.info(
            "  ★ %s threshold=%s  correctness=%.1f%%  avg_pnl=%.4f%%",
            rec["detector"],
            rec["threshold"],
            rec["correctness_rate"] * 100,
            rec["avg_pnl_pct"] * 100,
        )


if __name__ == "__main__":
    main()
