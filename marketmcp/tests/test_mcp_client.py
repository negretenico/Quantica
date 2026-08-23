"""End-to-end MCP client tests using in-memory transport.

An MCP Client connects in-process to the marketmcp MCPServer instance and
exercises resource listing, resource reads, tool invocations, prompt listing,
prompt gets, and error handling.  The MarketServerClient HTTP layer is mocked
so no live marketserver is required.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp.client import Client
from mcp.shared.exceptions import MCPError

# Ensure all decorator-registered tools/resources/prompts are loaded before
# the server is handed to a Client.  Without these imports the MCPServer
# instance has no handlers.
import mcp_server.prompts  # noqa: F401
import mcp_server.resources  # noqa: F401
import mcp_server.tools  # noqa: F401

# ---------------------------------------------------------------------------
# Fixture data — realistic trade blobs matching the pipeline schema
# ---------------------------------------------------------------------------

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
        "pnl_pct": 1.2,
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
        "pnl_pct": -0.5,
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

HEALTH_RESPONSE = {"status": "healthy", "status_code": 200}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_mock_client() -> MagicMock:
    """Create a mock MarketServerClient with deterministic return values."""
    mock = MagicMock()
    mock.get_trades_date_range = AsyncMock(return_value=SAMPLE_TRADES)
    mock.get_trades_for_date = AsyncMock(return_value=SAMPLE_TRADES)
    mock.get_blobs_for_date = AsyncMock(return_value=[])
    mock.get_health_details = AsyncMock(return_value=HEALTH_RESPONSE)
    return mock


@asynccontextmanager
async def _connected_client() -> AsyncIterator[Client]:
    """Create an MCP Client connected in-process with mocked HTTP layer.

    The Client context manager uses anyio task groups internally, so it must
    be entered and exited within the same async task.  Using this helper
    inside each test (rather than as a pytest fixture) avoids the cancel-scope
    mismatch that occurs when pytest-asyncio tears down a fixture in a
    different task.
    """
    from mcp_server.server import mcp as server

    mock = _build_mock_client()
    with (
        patch("mcp_server.tools._client", mock),
        patch("mcp_server.resources._client", mock),
        patch("mcp_server.resources.get_stream_instance", return_value=None),
        patch("mcp_server.resources._cache", {}),
    ):
        async with Client(server) as c:
            yield c


# ---------------------------------------------------------------------------
# 1. Resource listing
# ---------------------------------------------------------------------------


class TestResourceListing:
    async def test_list_resources_returns_expected_uris(self):
        async with _connected_client() as client:
            result = await client.list_resources()
            uris = {str(r.uri) for r in result.resources}

            assert "quantica://trades/latest" in uris
            assert "quantica://outcomes/recent" in uris
            assert "quantica://risk/state" in uris
            assert "quantica://health" in uris

    async def test_list_resource_templates_contains_parametric(self):
        async with _connected_client() as client:
            result = await client.list_resource_templates()
            template_uris = {t.uri_template for t in result.resource_templates}

            assert "quantica://trades/{symbol}/history" in template_uris
            assert "quantica://analytics/{symbol}" in template_uris


# ---------------------------------------------------------------------------
# 2. Resource read — quantica://trades/latest
# ---------------------------------------------------------------------------


class TestResourceRead:
    async def test_read_trades_latest_returns_valid_json(self):
        async with _connected_client() as client:
            result = await client.read_resource("quantica://trades/latest")

            assert result.contents, "Expected at least one content block"
            text = result.contents[0].text
            data = json.loads(text)
            assert isinstance(data, list)
            assert len(data) == len(SAMPLE_TRADES)

    async def test_read_health_returns_status(self):
        async with _connected_client() as client:
            result = await client.read_resource("quantica://health")

            text = result.contents[0].text
            data = json.loads(text)
            assert data["status"] == "healthy"


# ---------------------------------------------------------------------------
# 3. Tool invocation — query_signals with filters
# ---------------------------------------------------------------------------


class TestToolQuerySignals:
    async def test_query_signals_returns_results(self):
        async with _connected_client() as client:
            result = await client.call_tool(
                "query_signals",
                {"start_date": "2026-01-15", "end_date": "2026-01-15"},
            )

            assert not result.is_error
            text = result.content[0].text
            data = json.loads(text)
            assert isinstance(data, list)
            assert len(data) == 3

    async def test_query_signals_filters_by_symbol(self):
        async with _connected_client() as client:
            result = await client.call_tool(
                "query_signals",
                {
                    "start_date": "2026-01-15",
                    "end_date": "2026-01-15",
                    "symbol": "BTCUSDT",
                },
            )

            data = json.loads(result.content[0].text)
            assert len(data) == 2
            assert all(t["symbol"] == "BTCUSDT" for t in data)

    async def test_query_signals_filters_by_min_anomaly_score(self):
        async with _connected_client() as client:
            result = await client.call_tool(
                "query_signals",
                {
                    "start_date": "2026-01-15",
                    "end_date": "2026-01-15",
                    "min_anomaly_score": 0.9,
                },
            )

            data = json.loads(result.content[0].text)
            assert len(data) == 1
            assert data[0]["anomaly_score"] >= 0.9


# ---------------------------------------------------------------------------
# 4. Tool invocation — get_dashboard_summary
# ---------------------------------------------------------------------------


class TestToolDashboardSummary:
    async def test_dashboard_summary_has_required_keys(self):
        async with _connected_client() as client:
            result = await client.call_tool("get_dashboard_summary", {})

            assert not result.is_error
            data = json.loads(result.content[0].text)
            assert "signals_processed" in data
            assert "trades_executed" in data
            assert "symbols_active" in data
            assert "risk_rejections" in data

    async def test_dashboard_summary_counts_are_correct(self):
        async with _connected_client() as client:
            result = await client.call_tool("get_dashboard_summary", {})
            data = json.loads(result.content[0].text)

            assert data["signals_processed"] == 3
            # 2 trades have risk_approved=True
            assert data["trades_executed"] == 2
            # 1 trade has risk_approved=False
            assert data["risk_rejections"] == 1
            assert set(data["symbols_active"]) == {"BTCUSDT", "ETHUSDT"}


# ---------------------------------------------------------------------------
# 5. Prompt listing
# ---------------------------------------------------------------------------


class TestPromptListing:
    async def test_list_prompts_returns_expected_names(self):
        async with _connected_client() as client:
            result = await client.list_prompts()
            names = {p.name for p in result.prompts}

            assert "market_briefing" in names
            assert "risk_report" in names
            assert "anomaly_investigation" in names

    async def test_market_briefing_has_argument_schema(self):
        async with _connected_client() as client:
            result = await client.list_prompts()
            briefing = next(
                p for p in result.prompts if p.name == "market_briefing"
            )

            arg_names = {a.name for a in (briefing.arguments or [])}
            assert "hours_back" in arg_names

    async def test_anomaly_investigation_requires_symbol(self):
        async with _connected_client() as client:
            result = await client.list_prompts()
            investigation = next(
                p for p in result.prompts if p.name == "anomaly_investigation"
            )

            args = {a.name: a for a in (investigation.arguments or [])}
            assert "symbol" in args
            assert args["symbol"].required is True


# ---------------------------------------------------------------------------
# 6. Prompt get — market_briefing returns structured messages
# ---------------------------------------------------------------------------


class TestPromptGet:
    async def test_get_market_briefing_returns_messages(self):
        async with _connected_client() as client:
            result = await client.get_prompt(
                "market_briefing", {"hours_back": "1"}
            )

            assert result.messages is not None
            assert len(result.messages) >= 1
            first = result.messages[0]
            assert first.role == "user"

    async def test_get_anomaly_investigation_embeds_resource_refs(self):
        async with _connected_client() as client:
            result = await client.get_prompt(
                "anomaly_investigation", {"symbol": "BTCUSDT"}
            )

            assert result.messages is not None
            assert len(result.messages) >= 2


# ---------------------------------------------------------------------------
# 7. Error handling — non-existent resource / tool
# ---------------------------------------------------------------------------


class TestErrorHandling:
    async def test_read_nonexistent_resource_raises_error(self):
        async with _connected_client() as client:
            with pytest.raises(MCPError):
                await client.read_resource("quantica://does-not-exist")

    async def test_call_nonexistent_tool_returns_error(self):
        async with _connected_client() as client:
            result = await client.call_tool("nonexistent_tool", {})
            assert result.is_error
            assert "Unknown tool" in result.content[0].text
