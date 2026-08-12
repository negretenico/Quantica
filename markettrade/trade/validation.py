from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable

from pydantic import ValidationError

from trade.models import SignalEvent

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    valid: bool
    reason: str | None = None
    detail: str | None = None
    event: SignalEvent | None = None


def validate_schema(payload: dict) -> ValidationResult:
    """Parse payload into a SignalEvent. Rejects on any Pydantic ValidationError."""
    try:
        event = SignalEvent(**payload)
    except ValidationError as e:
        reason = str(e.errors()[0]["loc"][0]) if e.errors() else "unknown"
        return ValidationResult(
            valid=False,
            reason=reason,
            detail=str(e),
        )
    return ValidationResult(valid=True, event=event)


def validate_price_sanity(
    payload: dict, *, enabled: bool, min_price: float, max_price: float
) -> ValidationResult:
    """Check that price is present, numeric, and within configured bounds."""
    if not enabled:
        return ValidationResult(valid=True)

    price = payload.get("price")
    if price is None:
        return ValidationResult(
            valid=False,
            reason="price_missing",
            detail="price field is absent",
        )

    try:
        price_f = float(price)
    except (TypeError, ValueError):
        return ValidationResult(
            valid=False,
            reason="price_invalid",
            detail=f"price={price!r} is not numeric",
        )

    if price_f < min_price or price_f > max_price:
        return ValidationResult(
            valid=False,
            reason="price_out_of_range",
            detail=f"price={price_f} outside [{min_price}, {max_price}]",
        )
    return ValidationResult(valid=True)


class ValidationPipeline:
    """Runs an ordered list of validators, stopping at the first failure.

    Each validator is a ``Callable[[dict], ValidationResult]``.  The schema
    validator should be first; its ``.event`` is carried forward on the final
    success result so callers can use the parsed ``SignalEvent``.
    """

    def __init__(self, validators: list[Callable[[dict], ValidationResult]]):
        self._validators = validators

    def run(self, payload: dict) -> ValidationResult:
        event: SignalEvent | None = None
        for validator in self._validators:
            result = validator(payload)
            if result.event is not None:
                event = result.event
            if not result.valid:
                return result
        return ValidationResult(valid=True, event=event)
