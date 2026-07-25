"""
loader.py — Stream a JSONL dump file as normalized trade dicts.

Precondition: the file must be event-time ordered as produced by ``dump_topic.py``.
The loader does not sort — it yields lines in the order they appear on disk.

Each yielded dict has the following normalized keys:

    symbol    (str)   — trading pair, e.g. "BTCUSDT"
    price     (str)   — trade price as a string, e.g. "66157.90"
    quantity  (str)   — trade quantity as a string, e.g. "0.042"
    side      (str)   — "BUY" or "SELL" (derived from Binance ``m`` field:
                        m=false → BUY aggressor, m=true → SELL aggressor,
                        matching BinanceStreamResponse.getTradeSide() in markettransformer)
    eventTime (int)   — Binance event timestamp in milliseconds

Malformed lines (JSON parse errors, missing required raw fields) are logged as
warnings and skipped.
"""

import json
import logging
from collections.abc import Iterator

log = logging.getLogger(__name__)

_REQUIRED_RAW = ("s", "p", "q", "m", "E")


def load_dump(path: str) -> Iterator[dict]:
    """Yield normalized trade dicts from a JSONL dump file.

    Args:
        path: Absolute or relative path to a ``dump/*.jsonl`` file produced by
              ``dump_topic.py``.

    Yields:
        Dicts with keys: ``symbol``, ``price``, ``quantity``, ``side``, ``eventTime``.
    """
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue

            try:
                record = json.loads(raw)
            except json.JSONDecodeError as exc:
                log.warning("line %d: JSON parse error — %s", lineno, exc)
                continue

            missing = [k for k in _REQUIRED_RAW if k not in record]
            if missing:
                log.warning("line %d: missing required fields %s — skipping", lineno, missing)
                continue

            m: bool = record["m"]
            yield {
                "symbol": record["s"],
                "price": record["p"],
                "quantity": record["q"],
                "side": "SELL" if m else "BUY",
                "eventTime": record["E"],
            }
