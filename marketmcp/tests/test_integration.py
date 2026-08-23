"""Integration tests — require a running marketserver instance.

Marked with @pytest.mark.integration and skipped if marketserver is unreachable.
"""

import json

import httpx
import pytest

from app.config import Config

_config = Config()
_base_url = _config.MARKETSERVER_BASE_URL


def _marketserver_available() -> bool:
    try:
        resp = httpx.get(f"{_base_url}/health", timeout=3)
        return resp.status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _marketserver_available(),
        reason="marketserver not reachable",
    ),
]


class TestQuerySignalsIntegration:
    @pytest.mark.asyncio
    async def test_query_signals_returns_list(self):
        from mcp_server.tools import query_signals
        from datetime import date

        today = date.today().isoformat()
        result = json.loads(await query_signals(start_date=today, end_date=today))
        assert isinstance(result, list)


class TestGetTradeHistoryIntegration:
    @pytest.mark.asyncio
    async def test_get_trade_history_returns_list(self):
        from mcp_server.tools import get_trade_history

        result = json.loads(await get_trade_history(days_back=1))
        assert isinstance(result, list)


class TestGetDashboardSummaryIntegration:
    @pytest.mark.asyncio
    async def test_dashboard_summary_has_required_keys(self):
        from mcp_server.tools import get_dashboard_summary

        result = json.loads(await get_dashboard_summary())
        assert "signals_processed" in result
        assert "trades_executed" in result
        assert "symbols_active" in result


class TestTradesLatestIntegration:
    @pytest.mark.asyncio
    async def test_trades_latest_returns_json(self):
        from mcp_server.resources import trades_latest

        result = json.loads(await trades_latest())
        assert isinstance(result, list)


class TestHealthIntegration:
    @pytest.mark.asyncio
    async def test_health_returns_status(self):
        from mcp_server.resources import health

        result = json.loads(await health())
        assert "status" in result
