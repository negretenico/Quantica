import pytest
from marketrisk.risk.models import ProposedAction, RiskDecision


class TestProposedAction:
    def test_construction_and_field_access(self):
        action = ProposedAction(
            symbol="BTCUSDT",
            action="BUY",
            entry_price=42_000.50,
            raw_quantity=0.25,
            portfolio_value=10_000.00,
        )
        assert action.symbol == "BTCUSDT"
        assert action.action == "BUY"
        assert action.entry_price == 42_000.50
        assert action.raw_quantity == 0.25
        assert action.portfolio_value == 10_000.00

    def test_frozen_prevents_mutation(self):
        action = ProposedAction(
            symbol="BTCUSDT",
            action="BUY",
            entry_price=42_000.50,
            raw_quantity=0.25,
            portfolio_value=10_000.00,
        )
        with pytest.raises(Exception):
            action.symbol = "ETHUSDT"  # type: ignore[misc]

    def test_equality_is_value_based(self):
        a = ProposedAction("BTCUSDT", "BUY", 42_000.50, 0.25, 10_000.00)
        b = ProposedAction("BTCUSDT", "BUY", 42_000.50, 0.25, 10_000.00)
        assert a == b

    def test_inequality_on_differing_fields(self):
        a = ProposedAction("BTCUSDT", "BUY", 42_000.50, 0.25, 10_000.00)
        b = ProposedAction("ETHUSDT", "BUY", 42_000.50, 0.25, 10_000.00)
        assert a != b


class TestRiskDecision:
    def test_approved_with_sized_quantity(self):
        decision = RiskDecision(approved=True, sized_quantity=0.1, rejection_reason=None)
        assert decision.approved is True
        assert decision.sized_quantity == pytest.approx(0.1)
        assert decision.rejection_reason is None

    def test_rejected_with_reason(self):
        decision = RiskDecision(
            approved=False,
            sized_quantity=None,
            rejection_reason="exceeds max position size",
        )
        assert decision.approved is False
        assert decision.sized_quantity is None
        assert decision.rejection_reason == "exceeds max position size"

    def test_frozen_prevents_mutation(self):
        decision = RiskDecision(approved=True, sized_quantity=0.1, rejection_reason=None)
        with pytest.raises(Exception):
            decision.approved = False  # type: ignore[misc]

    def test_equality_is_value_based(self):
        a = RiskDecision(approved=True, sized_quantity=0.1, rejection_reason=None)
        b = RiskDecision(approved=True, sized_quantity=0.1, rejection_reason=None)
        assert a == b
