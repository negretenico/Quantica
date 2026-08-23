"""Shared utility functions for MCP server tools and resources."""

from __future__ import annotations


def compute_symbol_exposure(trades: list[dict], symbol: str, max_exposure: float) -> dict:
    """Compute exposure for a symbol from trade records.

    Sums sized_quantity for BUYs minus SELLs where risk_approved=True.

    Returns a dict with current_exposure, headroom, max_exposure, and trade_count.
    """
    symbol_trades = [
        t for t in trades
        if t.get("symbol") == symbol and t.get("risk_approved") is True
    ]

    current_exposure = 0.0
    for t in symbol_trades:
        sized_qty = float(t.get("sized_quantity", t.get("quantity", 0)))
        side = t.get("side", "").upper()
        if side == "BUY":
            current_exposure += sized_qty
        elif side == "SELL":
            current_exposure -= sized_qty

    headroom = max_exposure - current_exposure

    return {
        "symbol": symbol,
        "current_exposure": round(current_exposure, 6),
        "max_exposure": max_exposure,
        "headroom": round(headroom, 6),
        "trade_count": len(symbol_trades),
    }
