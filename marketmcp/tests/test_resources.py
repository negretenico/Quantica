"""Unit tests for MCP resources, mocking the HTTP client."""

import json
import time
from unittest.mock import AsyncMock, patch

import pytest


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

TRADES_WITH_PNL = [
    {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "risk_approved": True,
        "pnl_pct": 2.5,
        "sized_quantity": 0.5,
    },
    {
        "symbol": "ETHUSDT",
        "side": "BUY",
        "risk_approved": True,
        # no pnl_pct — should be skipped
        "sized_quantity": 1.0,
    },
    {
        "symbol": "BTCUSDT",
        "side": "SELL",
        "risk_approved": False,
        "pnl_pct": -1.0,
        "sized_quantity": 0.2,
    },
]


@pytest.fixture(autouse=True)
def mock_client():
    """Mock the MarketServerClient used by resources module."""
    with patch("mcp_server.resources._client") as mock:
        mock.get_trades_date_range = AsyncMock(return_value=SAMPLE_TRADES)
        mock.get_trades_for_date = AsyncMock(return_value=SAMPLE_TRADES)
        mock.get_blobs_for_date = AsyncMock(return_value=[])
        mock.get_blobs_date_range = AsyncMock(return_value=[])
        mock.get_health_details = AsyncMock(
            return_value={"status": "healthy", "status_code": 200}
        )
        yield mock


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the resource cache before each test."""
    from mcp_server.resources import _cache

    _cache.clear()
    yield
    _cache.clear()


class TestTradesLatest:
    @pytest.mark.asyncio
    async def test_returns_todays_trades(self):
        from mcp_server.resources import trades_latest

        result = json.loads(await trades_latest())
        assert isinstance(result, list)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_handles_empty(self, mock_client):
        from mcp_server.resources import trades_latest

        mock_client.get_trades_for_date = AsyncMock(return_value=[])
        result = json.loads(await trades_latest())
        assert result == []

    @pytest.mark.asyncio
    async def test_handles_errors(self, mock_client):
        from mcp_server.resources import trades_latest

        mock_client.get_trades_for_date = AsyncMock(
            side_effect=Exception("connection failed")
        )
        result = json.loads(await trades_latest())
        assert "error" in result


class TestTradeHistory:
    @pytest.mark.asyncio
    async def test_filters_by_symbol(self):
        from mcp_server.resources import trade_history

        result = json.loads(await trade_history(symbol="BTCUSDT"))
        assert len(result) == 2
        assert all(t["symbol"] == "BTCUSDT" for t in result)

    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_symbol(self):
        from mcp_server.resources import trade_history

        result = json.loads(await trade_history(symbol="XRPUSDT"))
        assert result == []


class TestAnalyticsSymbol:
    @pytest.mark.asyncio
    async def test_computes_correct_summary(self):
        from mcp_server.resources import analytics_symbol

        result = json.loads(await analytics_symbol(symbol="BTCUSDT"))
        assert result["symbol"] == "BTCUSDT"
        assert result["count"] == 2
        # avg of 0.85 and 0.92 = 0.885
        assert abs(result["avg_anomaly_score"] - 0.885) < 0.001
        assert result["dominant_cluster"] == 3

    @pytest.mark.asyncio
    async def test_unknown_symbol_returns_zero_count(self):
        from mcp_server.resources import analytics_symbol

        result = json.loads(await analytics_symbol(symbol="XRPUSDT"))
        assert result["count"] == 0
        assert result["avg_anomaly_score"] is None


class TestOutcomesRecent:
    @pytest.mark.asyncio
    async def test_filters_to_approved_with_pnl_pct(self, mock_client):
        from mcp_server.resources import outcomes_recent

        mock_client.get_trades_date_range = AsyncMock(return_value=TRADES_WITH_PNL)
        result = json.loads(await outcomes_recent())
        # Only first entry has risk_approved=True AND pnl_pct
        assert len(result) == 1
        assert result[0]["symbol"] == "BTCUSDT"
        assert result[0]["pnl_pct"] == 2.5

    @pytest.mark.asyncio
    async def test_skips_entries_without_pnl_pct(self, mock_client):
        from mcp_server.resources import outcomes_recent

        mock_client.get_trades_date_range = AsyncMock(return_value=TRADES_WITH_PNL)
        result = json.loads(await outcomes_recent())
        # ETHUSDT is approved but lacks pnl_pct — excluded
        symbols = [t["symbol"] for t in result]
        assert "ETHUSDT" not in symbols


class TestRiskState:
    @pytest.mark.asyncio
    async def test_computes_per_symbol_exposure(self):
        from mcp_server.resources import risk_state

        result = json.loads(await risk_state())
        assert "symbols" in result
        assert "near_limit_symbols" in result
        symbols = {s["symbol"] for s in result["symbols"]}
        # Only approved trades contribute: BTCUSDT (buy 0.5) and ETHUSDT (sell 2.0)
        assert "BTCUSDT" in symbols
        assert "ETHUSDT" in symbols

    @pytest.mark.asyncio
    async def test_identifies_near_limit(self, mock_client):
        from mcp_server.resources import risk_state

        # Create trades that push BTCUSDT above 80% of max (1.0)
        near_limit_trades = [
            {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "sized_quantity": 0.9,
                "risk_approved": True,
            },
        ]
        mock_client.get_trades_date_range = AsyncMock(return_value=near_limit_trades)
        result = json.loads(await risk_state())
        near = result["near_limit_symbols"]
        assert len(near) == 1
        assert near[0]["symbol"] == "BTCUSDT"


class TestHealth:
    @pytest.mark.asyncio
    async def test_returns_health_status(self):
        from mcp_server.resources import health

        result = json.loads(await health())
        assert result["status"] == "healthy"
        assert "checked_at" in result


class TestCaching:
    @pytest.mark.asyncio
    async def test_cache_hit_avoids_second_call(self, mock_client):
        from mcp_server.resources import trades_latest

        await trades_latest()
        await trades_latest()
        # Should only call get_trades_for_date once due to cache
        assert mock_client.get_trades_for_date.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_expiry_triggers_refresh(self, mock_client):
        from mcp_server.resources import _cache, trades_latest

        await trades_latest()
        assert mock_client.get_trades_for_date.call_count == 1

        # Expire the cache entry manually
        for key in list(_cache.keys()):
            expiry, data = _cache[key]
            _cache[key] = (time.time() - 1, data)

        await trades_latest()
        assert mock_client.get_trades_for_date.call_count == 2
