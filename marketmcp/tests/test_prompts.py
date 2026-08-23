"""Unit tests for MCP prompts."""

import pytest

from mcp.server.mcpserver.prompts.base import UserMessage
from mcp.types import EmbeddedResource, TextContent


class TestMarketBriefingPrompt:
    @pytest.mark.asyncio
    async def test_returns_list_of_messages(self):
        from mcp_server.prompts import market_briefing

        result = await market_briefing()
        assert isinstance(result, list)
        assert all(isinstance(m, UserMessage) for m in result)

    @pytest.mark.asyncio
    async def test_default_hours_back(self):
        from mcp_server.prompts import market_briefing

        result = await market_briefing()
        text_msg = result[0]
        assert isinstance(text_msg.content, TextContent)
        assert "24 hours" in text_msg.content.text

    @pytest.mark.asyncio
    async def test_custom_hours_back(self):
        from mcp_server.prompts import market_briefing

        result = await market_briefing(hours_back=6)
        text_msg = result[0]
        assert isinstance(text_msg.content, TextContent)
        assert "6 hours" in text_msg.content.text
        assert "24 hours" not in text_msg.content.text

    @pytest.mark.asyncio
    async def test_embeds_correct_resources(self):
        from mcp_server.prompts import market_briefing

        result = await market_briefing()
        resource_uris = _extract_resource_uris(result)
        assert "quantica://trades/latest" in resource_uris
        assert "quantica://outcomes/recent" in resource_uris
        assert "quantica://risk/state" in resource_uris

    @pytest.mark.asyncio
    async def test_has_four_messages(self):
        from mcp_server.prompts import market_briefing

        result = await market_briefing()
        # 1 text + 3 embedded resources
        assert len(result) == 4


class TestRiskReportPrompt:
    @pytest.mark.asyncio
    async def test_returns_list_of_messages(self):
        from mcp_server.prompts import risk_report

        result = await risk_report()
        assert isinstance(result, list)
        assert all(isinstance(m, UserMessage) for m in result)

    @pytest.mark.asyncio
    async def test_template_text(self):
        from mcp_server.prompts import risk_report

        result = await risk_report()
        text_msg = result[0]
        assert isinstance(text_msg.content, TextContent)
        assert "risk exposure" in text_msg.content.text
        assert "near-limit" in text_msg.content.text

    @pytest.mark.asyncio
    async def test_embeds_correct_resources(self):
        from mcp_server.prompts import risk_report

        result = await risk_report()
        resource_uris = _extract_resource_uris(result)
        assert "quantica://risk/state" in resource_uris
        assert "quantica://outcomes/recent" in resource_uris

    @pytest.mark.asyncio
    async def test_has_three_messages(self):
        from mcp_server.prompts import risk_report

        result = await risk_report()
        # 1 text + 2 embedded resources
        assert len(result) == 3


class TestAnomalyInvestigationPrompt:
    @pytest.mark.asyncio
    async def test_returns_list_of_messages(self):
        from mcp_server.prompts import anomaly_investigation

        result = await anomaly_investigation(symbol="BTCUSDT")
        assert isinstance(result, list)
        assert all(isinstance(m, UserMessage) for m in result)

    @pytest.mark.asyncio
    async def test_includes_symbol_in_text(self):
        from mcp_server.prompts import anomaly_investigation

        result = await anomaly_investigation(symbol="ETHUSDT")
        text_msg = result[0]
        assert isinstance(text_msg.content, TextContent)
        assert "ETHUSDT" in text_msg.content.text

    @pytest.mark.asyncio
    async def test_embeds_correct_resources(self):
        from mcp_server.prompts import anomaly_investigation

        result = await anomaly_investigation(symbol="BTCUSDT")
        resource_uris = _extract_resource_uris(result)
        assert "quantica://trades/BTCUSDT/history" in resource_uris
        assert "quantica://analytics/BTCUSDT" in resource_uris

    @pytest.mark.asyncio
    async def test_resource_uris_use_symbol(self):
        from mcp_server.prompts import anomaly_investigation

        result = await anomaly_investigation(symbol="SOLUSDT")
        resource_uris = _extract_resource_uris(result)
        assert "quantica://trades/SOLUSDT/history" in resource_uris
        assert "quantica://analytics/SOLUSDT" in resource_uris

    @pytest.mark.asyncio
    async def test_has_three_messages(self):
        from mcp_server.prompts import anomaly_investigation

        result = await anomaly_investigation(symbol="BTCUSDT")
        # 1 text + 2 embedded resources
        assert len(result) == 3


def _extract_resource_uris(messages: list[UserMessage]) -> list[str]:
    """Extract embedded resource URIs from a list of messages."""
    uris = []
    for msg in messages:
        if isinstance(msg.content, EmbeddedResource):
            uris.append(msg.content.resource.uri)
    return uris
