from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum


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


@dataclass(frozen=True)
class NearLimitAlert:
    symbol: str
    current_exposure: float
    max_exposure: float
    ratio: float
    timestamp_utc: str

    def to_dict(self) -> dict:
        return {"alert_type": "near_limit", **asdict(self)}


@dataclass(frozen=True)
class NearLimitCleared:
    symbol: str
    timestamp_utc: str

    def to_dict(self) -> dict:
        return asdict(self)


class ConcentrationState(Enum):
    """State machine for concentration risk alerting.

    ARMED → FIRED: count crosses >= threshold, emits ConcentrationAlert
    FIRED → FIRED: count stays >= threshold, no-op
    FIRED → DISARMED: count drops < threshold, clears alert
    DISARMED → ARMED: count stays < threshold, re-arms for next crossing
    DISARMED → FIRED: count crosses >= threshold again, emits ConcentrationAlert
    """

    ARMED = "armed"
    FIRED = "fired"
    DISARMED = "disarmed"


@dataclass(frozen=True)
class ConcentrationAlert:
    near_limit_symbols: tuple[str, ...]
    symbol_ratios: dict[str, float]
    count: int
    threshold: int
    timestamp_utc: str

    def to_dict(self) -> dict:
        return {
            "alert_type": "concentration",
            "near_limit_symbols": list(self.near_limit_symbols),
            "symbol_ratios": dict(self.symbol_ratios),
            "count": self.count,
            "threshold": self.threshold,
            "timestamp_utc": self.timestamp_utc,
        }


@dataclass(frozen=True)
class ConcentrationCleared:
    remaining_count: int
    threshold: int
    timestamp_utc: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AccumulationAlert:
    symbol: str
    direction: str
    consecutive_count: int
    threshold: int
    timestamp_utc: str

    def to_dict(self) -> dict:
        return {"alert_type": "accumulation", **asdict(self)}


@dataclass(frozen=True)
class AccumulationCleared:
    symbol: str
    previous_direction: str
    new_direction: str
    timestamp_utc: str

    def to_dict(self) -> dict:
        return asdict(self)
