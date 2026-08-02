from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProposedAction:
    symbol: str
    action: str
    entry_price: float
    raw_quantity: float
    portfolio_value: float


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    sized_quantity: float | None
    rejection_reason: str | None
