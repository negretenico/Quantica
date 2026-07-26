"""
detectors.py — Pure-Python ports of the markettransformer signal detectors.

Each function accepts an iterable of trade dicts (as yielded by ``loader.load_dump``)
and returns a list of signal event dicts.  All state is local to the call; no state
is carried across calls (see :func:`price_spike` docstring for the implication on
chunked replay).

Trade dict shape (input)::

    {
        "symbol":    str,
        "price":     str,
        "quantity":  str,
        "side":      str,   # "BUY" | "SELL"
        "eventTime": int,
    }

Signal event dict shape (output) — mirrors Java ``SignalEvent`` exactly::

    {
        "symbol":    str,
        "eventTime": int,
        "type":      str,   # "LARGE_TRADE" | "PRICE_SPIKE" | "DOMINANT_SIDE"
        "reason":    str,
        "price":     float,
        "quantity":  float,
        "side":      str,
        "metadata":  dict,
    }
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable


def _signal(trade: dict, sig_type: str, reason: str, metadata: dict) -> dict:
    """Build a signal event dict from a trade and detector-specific fields."""
    return {
        "symbol": trade["symbol"],
        "eventTime": trade["eventTime"],
        "type": sig_type,
        "reason": reason,
        "price": float(trade["price"]),
        "quantity": float(trade["quantity"]),
        "side": trade["side"],
        "metadata": metadata,
    }


def large_trade(
    stream: Iterable[dict],
    threshold: float = 1_000_000,
) -> list[dict]:
    """Return signals for trades whose quantity strictly exceeds *threshold*.

    Mirrors ``LargeTradeDetected.onApplicationEvent`` in markettransformer.
    The boundary value does **not** fire (``quantity > threshold``, not ``>=``),
    matching Java's ``compareTo(MILLION) <= 0`` early-return.

    Args:
        stream:    Iterable of trade dicts from ``loader.load_dump``.
        threshold: Quantity threshold in base units.  Defaults to 1,000,000.

    Returns:
        List of signal event dicts with ``type == "LARGE_TRADE"``.
    """
    signals: list[dict] = []
    for trade in stream:
        qty = float(trade["quantity"])
        if qty <= threshold:
            continue
        reason = f"Quantity {trade['quantity']} exceeded threshold {threshold}"
        signals.append(
            _signal(trade, "LARGE_TRADE", reason, {"threshold": threshold})
        )
    return signals


def price_spike(
    stream: Iterable[dict],
    window: int = 100,
    pct: float = 0.02,
) -> list[dict]:
    """Return signals for trades whose price deviates more than *pct* from the rolling average.

    Mirrors ``PriceSpike.onApplicationEvent`` in markettransformer.

    Per-symbol behaviour:
    - First trade seeds the rolling window and is skipped (no check performed).
    - Each subsequent trade computes the moving average over the current window,
      checks for a spike, then appends the price to the window.  This matches the
      Java ordering: check *before* append.
    - If the computed average is zero the trade is skipped (price still appended).

    State is **fresh per call**.  The moving average resets with each new
    ``price_spike(...)`` invocation.  Callers must not split a single dump into
    chunks and expect state continuity across chunks — pass the full stream in one
    call.

    Args:
        stream: Iterable of trade dicts from ``loader.load_dump``.
        window: Rolling window size (number of recent prices per symbol).
                Defaults to 100.
        pct:    Fractional deviation threshold (e.g. 0.02 == 2%).
                Defaults to 0.02.

    Returns:
        List of signal event dicts with ``type == "PRICE_SPIKE"``.
    """
    windows: dict[str, deque] = defaultdict(lambda: deque(maxlen=window))
    signals: list[dict] = []

    for trade in stream:
        symbol = trade["symbol"]
        price = float(trade["price"])
        buf = windows[symbol]

        if not buf:
            # First trade for this symbol: seed the window and skip the check.
            buf.append(price)
            continue

        avg = sum(buf) / len(buf)
        if avg == 0:
            buf.append(price)
            continue

        change = abs(price - avg) / avg
        if change > pct:
            reason = (
                f"Price {change * 100:.2f}% from moving average {avg:.4f} "
                f"exceeded threshold {pct * 100:.2f}%"
            )
            signals.append(
                _signal(
                    trade,
                    "PRICE_SPIKE",
                    reason,
                    {"priceChange": change, "movingAverage": avg, "threshold": pct},
                )
            )

        buf.append(price)

    return signals


def dominant_side(
    stream: Iterable[dict],
    streak: int = 5,
) -> list[dict]:
    """Return signals when one side dominates *streak* or more consecutive trades per symbol.

    Mirrors ``AggressiveBuyerSeller.onApplicationEvent`` in markettransformer.

    Per-symbol behaviour:
    - First trade initialises the streak to 1.
    - A side flip resets the streak to 1 (not 0) and updates the last-seen side.
    - Consecutive same-side trades increment the streak.
    - When ``streak_count >= streak`` a signal fires and the counter resets to 0,
      matching the Java ``streakCountBySymbol.put(symbol, 0)`` reset.

    Args:
        stream: Iterable of trade dicts from ``loader.load_dump``.
        streak: Minimum consecutive same-side trades required to fire.
                Defaults to 5.

    Returns:
        List of signal event dicts with ``type == "DOMINANT_SIDE"``.
    """
    last_side: dict[str, str] = {}
    streak_count: dict[str, int] = defaultdict(int)
    signals: list[dict] = []

    for trade in stream:
        symbol = trade["symbol"]
        side = trade["side"]

        if symbol not in last_side or last_side[symbol] != side:
            last_side[symbol] = side
            streak_count[symbol] = 1
        else:
            streak_count[symbol] += 1

        if streak_count[symbol] >= streak:
            count = streak_count[symbol]
            reason = f"{side} side dominated {count} trades"
            signals.append(
                _signal(trade, "DOMINANT_SIDE", reason, {"streakCount": count})
            )
            streak_count[symbol] = 0

    return signals
