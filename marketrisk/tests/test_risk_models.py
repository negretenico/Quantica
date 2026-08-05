import pytest
from marketrisk.risk.models import NearLimitAlert, ProposedAction, RiskDecision


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


class TestNearLimitAlert:
    def test_construction_and_field_access(self):
        alert = NearLimitAlert(
            symbol="BTCUSDT",
            current_exposure=4200.0,
            max_exposure=5000.0,
            ratio=0.84,
            timestamp_utc="2026-08-04T12:00:00+00:00",
        )
        assert alert.symbol == "BTCUSDT"
        assert alert.current_exposure == 4200.0
        assert alert.max_exposure == 5000.0
        assert alert.ratio == pytest.approx(0.84)
        assert alert.timestamp_utc == "2026-08-04T12:00:00+00:00"

    def test_frozen_prevents_mutation(self):
        alert = NearLimitAlert("BTCUSDT", 4200.0, 5000.0, 0.84, "2026-08-04T12:00:00+00:00")
        with pytest.raises(Exception):
            alert.symbol = "ETHUSDT"  # type: ignore[misc]

    def test_to_dict_returns_all_fields(self):
        alert = NearLimitAlert("BTCUSDT", 4200.0, 5000.0, 0.84, "2026-08-04T12:00:00+00:00")
        d = alert.to_dict()
        assert d == {
            "symbol": "BTCUSDT",
            "current_exposure": 4200.0,
            "max_exposure": 5000.0,
            "ratio": 0.84,
            "timestamp_utc": "2026-08-04T12:00:00+00:00",
        }

    def test_equality_is_value_based(self):
        a = NearLimitAlert("BTCUSDT", 4200.0, 5000.0, 0.84, "2026-08-04T12:00:00+00:00")
        b = NearLimitAlert("BTCUSDT", 4200.0, 5000.0, 0.84, "2026-08-04T12:00:00+00:00")
        assert a == b
