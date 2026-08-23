"""Unit tests for MCP tools, mocking the HTTP client."""

import json
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest


# Fixture data
SAMPLE_TRADES = [
    {
        "symbol": "BTCUSDT",
        "eventTime": "2026-01-15T10:00:00",
        "type": "AGGRESSIVE_BUY",
        "price": "50000",
        "quantity": "0.5",
        "side": "BUY",
        "anomaly_score": 0.85,
        "cluster_id": 3,
        "risk_approved": True,
        "sized_quantity": 0.5,
    },
    {
        "symbol": "ETHUSDT",
        "eventTime": "2026-01-15T10:01:00",
        "type": "AGGRESSIVE_SELL",
        "price": "3000",
        "quantity": "2.0",
        "side": "SELL",
        "anomaly_score": 0.3,
        "cluster_id": 1,
        "risk_approved": True,
        "sized_quantity": 2.0,
    },
    {
        "symbol": "BTCUSDT",
        "eventTime": "2026-01-15T10:02:00",
        "type": "AGGRESSIVE_BUY",
        "price": "50100",
        "quantity": "0.3",
        "side": "BUY",
        "anomaly_score": 0.92,
        "cluster_id": 3,
        "risk_approved": False,
        "sized_quantity": 0.3,
    },
]


@pytest.fixture(autouse=True)
def mock_client():
    """Mock the MarketServerClient used by tools module."""
    with patch("mcp_server.tools._client") as mock:
        mock.get_trades_date_range = AsyncMock(return_value=SAMPLE_TRADES)
        mock.get_trades_for_date = AsyncMock(return_value=SAMPLE_TRADES)
        mock.get_blobs_for_date = AsyncMock(return_value=[])
        yield mock


class TestQuerySignals:
    @pytest.mark.asyncio
    async def test_returns_all_in_range(self):
        from mcp_server.tools import query_signals

        result = json.loads(await query_signals(start_date="2026-01-15", end_date="2026-01-15"))
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_filters_by_symbol(self):
        from mcp_server.tools import query_signals

        result = json.loads(await query_signals(start_date="2026-01-15", end_date="2026-01-15", symbol="BTCUSDT"))
        assert len(result) == 2
        assert all(t["symbol"] == "BTCUSDT" for t in result)

    @pytest.mark.asyncio
    async def test_filters_by_signal_type(self):
        from mcp_server.tools import query_signals

        result = json.loads(await query_signals(start_date="2026-01-15", end_date="2026-01-15", signal_type="AGGRESSIVE_SELL"))
        assert len(result) == 1
        assert result[0]["symbol"] == "ETHUSDT"

    @pytest.mark.asyncio
    async def test_filters_by_min_anomaly_score(self):
        from mcp_server.tools import query_signals

        result = json.loads(await query_signals(start_date="2026-01-15", end_date="2026-01-15", min_anomaly_score=0.8))
        assert len(result) == 2
        assert all(t["anomaly_score"] >= 0.8 for t in result)

    @pytest.mark.asyncio
    async def test_empty_results(self, mock_client):
        from mcp_server.tools import query_signals

        mock_client.get_trades_date_range = AsyncMock(return_value=[])
        result = json.loads(await query_signals(start_date="2026-01-15", end_date="2026-01-15"))
        assert result == []

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_client):
        from mcp_server.tools import query_signals

        mock_client.get_trades_date_range = AsyncMock(side_effect=Exception("connection failed"))
        result = json.loads(await query_signals(start_date="2026-01-15", end_date="2026-01-15"))
        assert "error" in result


class TestGetRiskAssessment:
    @pytest.mark.asyncio
    async def test_computes_exposure(self):
        from mcp_server.tools import get_risk_assessment

        result = json.loads(await get_risk_assessment(symbol="BTCUSDT", action="BUY", quantity=0.1))
        # Only risk_approved=True BUY for BTCUSDT: 0.5
        assert result["current_exposure"] == 0.5
        assert result["symbol"] == "BTCUSDT"
        assert "headroom" in result
        assert "assessment" in result

    @pytest.mark.asyncio
    async def test_rejects_over_limit(self, mock_client):
        from mcp_server.tools import get_risk_assessment

        # With max exposure 1.0, current BTC exposure 0.5, buying 0.6 exceeds
        result = json.loads(await get_risk_assessment(symbol="BTCUSDT", action="BUY", quantity=0.6))
        assert result["approved"] is False
        assert "REJECTED" in result["assessment"]

    @pytest.mark.asyncio
    async def test_approves_within_limit(self):
        from mcp_server.tools import get_risk_assessment

        result = json.loads(await get_risk_assessment(symbol="BTCUSDT", action="BUY", quantity=0.1))
        assert result["approved"] is True
        assert result["assessment"] == "APPROVED"


class TestGetTradeHistory:
    @pytest.mark.asyncio
    async def test_returns_all_trades(self):
        from mcp_server.tools import get_trade_history

        result = json.loads(await get_trade_history())
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_filters_by_symbol(self):
        from mcp_server.tools import get_trade_history

        result = json.loads(await get_trade_history(symbol="ETHUSDT"))
        assert len(result) == 1
        assert result[0]["symbol"] == "ETHUSDT"


class TestExplainAnomaly:
    @pytest.mark.asyncio
    async def test_finds_matching_trade(self):
        from mcp_server.tools import explain_anomaly

        result = json.loads(await explain_anomaly(symbol="BTCUSDT", timestamp="2026-01-15T10:00:00"))
        assert result["cluster_id"] == 3
        assert result["anomaly_score"] == 0.85
        assert result["nearby_count"] >= 0

    @pytest.mark.asyncio
    async def test_not_found(self, mock_client):
        from mcp_server.tools import explain_anomaly

        mock_client.get_trades_for_date = AsyncMock(return_value=[])
        result = json.loads(await explain_anomaly(symbol="BTCUSDT", timestamp="2026-01-15T10:00:00"))
        assert "error" in result


class TestGetDashboardSummary:
    @pytest.mark.asyncio
    async def test_aggregates_correctly(self):
        from mcp_server.tools import get_dashboard_summary

        result = json.loads(await get_dashboard_summary(start_date="2026-01-15", end_date="2026-01-15"))
        assert result["signals_processed"] == 3
        assert result["trades_executed"] == 2  # 2 risk_approved=True
        assert result["risk_rejections"] == 1
        assert "BTCUSDT" in result["symbols_active"]
        assert "ETHUSDT" in result["symbols_active"]
        assert len(result["top_anomalies"]) <= 5

    @pytest.mark.asyncio
    async def test_defaults_to_today(self):
        from mcp_server.tools import get_dashboard_summary

        result = json.loads(await get_dashboard_summary())
        assert result["start_date"] == result["end_date"]
