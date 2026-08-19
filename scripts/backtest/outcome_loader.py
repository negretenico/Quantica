"""
outcome_loader.py — Load OutcomeRecord JSONL files written by markettrade's OutcomeWriter.

Files follow the ``decisions_YYYY-MM-DD.jsonl`` naming convention produced by
``shared.blob.disk_store.DiskStore``.  Each line is a JSON object with the
fields of ``OutcomeRecord`` (see ``markettrade/trade/outcome_tracker.py``).

Required fields per record::

    symbol           (str)
    action           (str)   — "BUY" | "SELL"
    entry_price      (float)
    decision_time    (str)   — ISO-8601 timestamp
    window_seconds   (int)
    outcome_price    (float)
    pnl_pct          (float)
    direction_correct (bool)
    recorded_at      (str)

Optional::

    anomaly_score    (float, default 0.0)
"""

from __future__ import annotations

import glob
import json
import logging
import os
from collections.abc import Iterator

log = logging.getLogger(__name__)

_REQUIRED_FIELDS = (
    "symbol",
    "action",
    "entry_price",
    "decision_time",
    "window_seconds",
    "outcome_price",
    "pnl_pct",
    "direction_correct",
    "recorded_at",
)


def load_outcomes(path: str) -> Iterator[dict]:
    """Yield outcome dicts from a file or directory of JSONL files.

    Args:
        path: A single ``.jsonl`` file **or** a directory containing
              ``decisions_*.jsonl`` files.

    Yields:
        Dicts with outcome record fields.
    """
    if os.path.isdir(path):
        pattern = os.path.join(path, "decisions_*.jsonl")
        files = sorted(glob.glob(pattern))
        if not files:
            log.warning("No decisions_*.jsonl files found in %s", path)
            return
        for fp in files:
            yield from _load_file(fp)
    else:
        yield from _load_file(path)


def _load_file(path: str) -> Iterator[dict]:
    """Yield validated outcome dicts from a single JSONL file."""
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue

            try:
                record = json.loads(raw)
            except json.JSONDecodeError as exc:
                log.warning("%s:%d: JSON parse error — %s", path, lineno, exc)
                continue

            missing = [k for k in _REQUIRED_FIELDS if k not in record]
            if missing:
                log.warning("%s:%d: missing fields %s — skipping", path, lineno, missing)
                continue

            yield record
