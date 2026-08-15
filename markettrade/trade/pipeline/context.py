from __future__ import annotations

from dataclasses import dataclass, field

from trade.models import SignalEvent


@dataclass
class PipelineContext:
    payload: dict
    event: SignalEvent | None = None
    decision: dict | None = None
    risk_decision: object | None = None
