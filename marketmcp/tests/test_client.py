"""Unit tests for MarketServerClient using httpx.MockTransport."""

import json
from datetime import date

import httpx
import pytest

from mcp_server.client import MarketServerClient


def _make_transport(handler):
    """Create a MockTransport from a handler function."""
    return httpx.MockTransport(handler)


def _jsonl_response(records: list[dict], status_code: int = 200) -> httpx.Response:
    body = "\n".join(json.dumps(r) for r in records)
    return httpx.Response(status_code, text=body)


class TestGetTradesForDate:
    @pytest.mark.asyncio
    async def test_parses_jsonl(self):
        records = [
            {"symbol": "BTCUSDT", "price": "50000", "type": "AGGRESSIVE_BUY"},
            {"symbol": "ETHUSDT", "price": "3000", "type": "AGGRESSIVE_SELL"},
        ]

        def handler(request: httpx.Request) -> httpx.Response:
            assert "/trades/2026-01-15" in str(request.url)
            return _jsonl_response(records)

        client = MarketServerClient.__new__(MarketServerClient)
        client._base_url = "http://test"
        client._max_query_days = 30
        client._client = httpx.AsyncClient(transport=_make_transport(handler), base_url="http://test")

        result = await client.get_trades_for_date(date(2026, 1, 15))
        assert len(result) == 2
        assert result[0]["symbol"] == "BTCUSDT"
        assert result[1]["price"] == "3000"
        await client.close()

    @pytest.mark.asyncio
    async def test_404_returns_empty_list(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, text="Not Found")

        client = MarketServerClient.__new__(MarketServerClient)
        client._base_url = "http://test"
        client._max_query_days = 30
        client._client = httpx.AsyncClient(transport=_make_transport(handler), base_url="http://test")

        result = await client.get_trades_for_date(date(2026, 1, 15))
        assert result == []
        await client.close()

    @pytest.mark.asyncio
    async def test_empty_body_returns_empty_list(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="")

        client = MarketServerClient.__new__(MarketServerClient)
        client._base_url = "http://test"
        client._max_query_days = 30
        client._client = httpx.AsyncClient(transport=_make_transport(handler), base_url="http://test")

        result = await client.get_trades_for_date(date(2026, 1, 15))
        assert result == []
        await client.close()


class TestGetTradesDateRange:
    @pytest.mark.asyncio
    async def test_iterates_days(self):
        call_dates = []

        def handler(request: httpx.Request) -> httpx.Response:
            path = str(request.url.path)
            call_dates.append(path)
            return _jsonl_response([{"symbol": "BTCUSDT", "date": path}])

        client = MarketServerClient.__new__(MarketServerClient)
        client._base_url = "http://test"
        client._max_query_days = 30
        client._client = httpx.AsyncClient(transport=_make_transport(handler), base_url="http://test")

        result = await client.get_trades_date_range(date(2026, 1, 1), date(2026, 1, 3))
        assert len(result) == 3
        assert len(call_dates) == 3
        await client.close()

    @pytest.mark.asyncio
    async def test_30_day_max_guard(self):
        client = MarketServerClient.__new__(MarketServerClient)
        client._base_url = "http://test"
        client._max_query_days = 30
        client._client = httpx.AsyncClient(transport=_make_transport(lambda r: httpx.Response(200, text="")))

        with pytest.raises(ValueError, match="exceeds maximum"):
            await client.get_trades_date_range(date(2026, 1, 1), date(2026, 3, 1))
        await client.close()

    @pytest.mark.asyncio
    async def test_end_before_start_returns_empty(self):
        client = MarketServerClient.__new__(MarketServerClient)
        client._base_url = "http://test"
        client._max_query_days = 30
        client._client = httpx.AsyncClient(transport=_make_transport(lambda r: httpx.Response(200, text="")))

        result = await client.get_trades_date_range(date(2026, 1, 5), date(2026, 1, 3))
        assert result == []
        await client.close()


class TestHealth:
    @pytest.mark.asyncio
    async def test_healthy(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="ok")

        client = MarketServerClient.__new__(MarketServerClient)
        client._base_url = "http://test"
        client._max_query_days = 30
        client._client = httpx.AsyncClient(transport=_make_transport(handler), base_url="http://test")

        assert await client.health() is True
        await client.close()

    @pytest.mark.asyncio
    async def test_unhealthy(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="error")

        client = MarketServerClient.__new__(MarketServerClient)
        client._base_url = "http://test"
        client._max_query_days = 30
        client._client = httpx.AsyncClient(transport=_make_transport(handler), base_url="http://test")

        assert await client.health() is False
        await client.close()
