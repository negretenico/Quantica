"""
evaluate.py — Threshold sweep over backtest detectors.

Runs each detector (large_trade, price_spike, dominant_side) across a
predefined range of thresholds, computes signal counts and fire rate, and
writes a summary CSV.

Usage::

    py scripts/backtest/evaluate.py --dump-path dump/trades.jsonl
    py scripts/backtest/evaluate.py --dump-path dump/trades.jsonl --output-dir results/

Output: <output-dir>/threshold_sweep.csv
Columns: detector, threshold, fire_count, fire_rate_per_1k_trades
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys

# Allow running as a script from the repo root or from within scripts/backtest/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from scripts.backtest.detectors import dominant_side, large_trade, price_spike
from scripts.backtest.loader import load_dump

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Threshold ranges
# ---------------------------------------------------------------------------

_LARGE_TRADE_THRESHOLDS: list[float] = [
    100_000,
    250_000,
    500_000,
    750_000,
    1_000_000,
    2_000_000,
    5_000_000,
]

_PRICE_SPIKE_PCTS: list[float] = [0.005, 0.01, 0.015, 0.02, 0.03, 0.05, 0.10]

_DOMINANT_SIDE_STREAKS: list[int] = [3, 4, 5, 6, 7, 8, 10]

CSV_COLUMNS = ["detector", "threshold", "fire_count", "fire_rate_per_1k_trades"]


# ---------------------------------------------------------------------------
# Sweep
# ---------------------------------------------------------------------------


def sweep(trades: list[dict]) -> list[dict]:
    """Run all detectors across their threshold ranges.

    Args:
        trades: Pre-loaded list of trade dicts from ``loader.load_dump``.

    Returns:
        List of result dicts with keys matching ``CSV_COLUMNS``.
    """
    total = len(trades)
    rows: list[dict] = []

    for threshold in _LARGE_TRADE_THRESHOLDS:
        signals = large_trade(trades, threshold=threshold)
        fire_count = len(signals)
        rows.append(
            {
                "detector": "large_trade",
                "threshold": threshold,
                "fire_count": fire_count,
                "fire_rate_per_1k_trades": round(fire_count / total * 1_000, 4) if total else 0.0,
            }
        )

    for pct in _PRICE_SPIKE_PCTS:
        signals = price_spike(trades, pct=pct)
        fire_count = len(signals)
        rows.append(
            {
                "detector": "price_spike",
                "threshold": pct,
                "fire_count": fire_count,
                "fire_rate_per_1k_trades": round(fire_count / total * 1_000, 4) if total else 0.0,
            }
        )

    for streak in _DOMINANT_SIDE_STREAKS:
        signals = dominant_side(trades, streak=streak)
        fire_count = len(signals)
        rows.append(
            {
                "detector": "dominant_side",
                "threshold": streak,
                "fire_count": fire_count,
                "fire_rate_per_1k_trades": round(fire_count / total * 1_000, 4) if total else 0.0,
            }
        )

    return rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Threshold sweep over backtest detectors. Outputs threshold_sweep.csv."
    )
    parser.add_argument(
        "--dump-path",
        required=True,
        help="Path to a JSONL dump file produced by dump_topic.py.",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(os.path.dirname(__file__), "results"),
        help="Directory to write threshold_sweep.csv (default: scripts/backtest/results/).",
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

    rows = sweep(trades)

    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, "threshold_sweep.csv")

    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    log.info("Wrote %d rows → %s", len(rows), out_path)


if __name__ == "__main__":
    main()
