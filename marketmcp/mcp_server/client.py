"""Async HTTP client wrapping marketserver API calls."""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta

import httpx

logger = logging.getLogger(__name__)


class MarketServerClient:
    """HTTP client for marketserver REST API."""

    def __init__(self, base_url: str, max_query_days: int = 30) -> None:
        self._base_url = base_url.rstrip("/")
        self._max_query_days = max_query_days
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=30.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def get_trades_for_date(self, d: date) -> list[dict]:
        """GET /trades/{date}, parse JSONL response, return [] on 404."""
        return await self._fetch_jsonl(f"/trades/{d.isoformat()}")

    async def get_blobs_for_date(self, d: date) -> list[dict]:
        """GET /blobs/{date}, parse JSONL response, return [] on 404."""
        return await self._fetch_jsonl(f"/blobs/{d.isoformat()}")

    async def get_trades_date_range(self, start: date, end: date) -> list[dict]:
        """Fetch trades across a date range. Max 30-day guard."""
        days = (end - start).days + 1
        if days > self._max_query_days:
            raise ValueError(
                f"Date range {days} days exceeds maximum of {self._max_query_days}"
            )
        if days < 1:
            return []

        results: list[dict] = []
        current = start
        while current <= end:
            trades = await self.get_trades_for_date(current)
            results.extend(trades)
            current += timedelta(days=1)
        return results

    async def get_blobs_date_range(self, start: date, end: date) -> list[dict]:
        """Fetch blobs across a date range. Max 30-day guard."""
        days = (end - start).days + 1
        if days > self._max_query_days:
            raise ValueError(
                f"Date range {days} days exceeds maximum of {self._max_query_days}"
            )
        if days < 1:
            return []

        results: list[dict] = []
        current = start
        while current <= end:
            blobs = await self.get_blobs_for_date(current)
            results.extend(blobs)
            current += timedelta(days=1)
        return results

    async def health(self) -> bool:
        """Check if marketserver is reachable."""
        try:
            resp = await self._client.get("/health")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def get_health_details(self) -> dict:
        """Get health details from marketserver. Returns dict with status info."""
        try:
            resp = await self._client.get("/health")
            if resp.status_code == 200:
                try:
                    return resp.json()
                except Exception:
                    return {"status": "healthy", "status_code": resp.status_code}
            return {"status": "unhealthy", "status_code": resp.status_code}
        except httpx.HTTPError as e:
            return {"status": "unreachable", "error": str(e)}

    async def _fetch_jsonl(self, path: str) -> list[dict]:
        """Fetch a JSONL endpoint and parse each line as JSON."""
        try:
            resp = await self._client.get(path)
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error fetching %s: %s", path, e)
            raise

        results: list[dict] = []
        for line in resp.text.strip().splitlines():
            line = line.strip()
            if line:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning("Skipping unparseable JSONL line: %s", line[:100])
        return results
