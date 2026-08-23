"""MCP resource definitions for marketmcp.

Resources expose pipeline data (trades, analytics, risk, outcomes, health)
as readable MCP resources fetched from marketserver.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC as _UTC
from datetime import date, datetime, timedelta

from app.config import Config
from app.metrics import (
    mcp_errors_total,
    resource_latency_seconds,
    resource_requests_total,
)
from mcp_server.client import MarketServerClient
from mcp_server.server import mcp
from mcp_server.utils import compute_symbol_exposure

logger = logging.getLogger(__name__)

_config = Config()
_client = MarketServerClient(
    base_url=_config.MARKETSERVER_BASE_URL,
    max_query_days=_config.MAX_QUERY_DAYS,
)

# ---------------------------------------------------------------------------
# Simple dict-based TTL cache
# ---------------------------------------------------------------------------
_cache: dict[str, tuple[float, str]] = {}  # uri -> (expiry_time, json_string)
MAX_CACHE_ENTRIES = 200


def _cache_get(uri: str) -> str | None:
    """Return cached value if not expired, else None."""
    entry = _cache.get(uri)
    if entry is None:
        return None
    expiry, data = entry
    if time.time() > expiry:
        del _cache[uri]
        return None
    return data


def _cache_set(uri: str, data: str) -> None:
    """Store data with expiry = now + TTL. Clear all if cache exceeds limit."""
    if len(_cache) >= MAX_CACHE_ENTRIES:
        _cache.clear()
    _cache[uri] = (time.time() + _config.RESOURCE_CACHE_TTL_SECONDS, data)


def _error(resource_name: str, msg: str) -> str:
    """Log and count an error, return JSON error response."""
    mcp_errors_total.labels(tool=resource_name).inc()
    logger.error("[%s] %s", resource_name, msg)
    return json.dumps({"error": msg})


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource(
    "quantica://trades/latest",
    name="trades_latest",
    description="Latest trade events across all symbols (today)",
    mime_type="application/json",
)
async def trades_latest() -> str:
    """Fetch today's trades and return as JSON array."""
    resource_name = "trades_latest"
    resource_requests_total.labels(resource=resource_name).inc()
    start = time.perf_counter()
    try:
        cached = _cache_get("quantica://trades/latest")
        if cached is not None:
            return cached

        today = date.today()
        trades = await _client.get_trades_for_date(today)
        result = json.dumps(trades, default=str)
        _cache_set("quantica://trades/latest", result)
        return result
    except Exception as e:
        return _error(resource_name, str(e))
    finally:
        resource_latency_seconds.labels(resource=resource_name).observe(
            time.perf_counter() - start
        )


@mcp.resource(
    "quantica://trades/{symbol}/history",
    name="trade_history",
    description="Trade history for a specific symbol",
    mime_type="application/json",
)
async def trade_history(symbol: str) -> str:
    """Fetch last N days of trades filtered by symbol."""
    resource_name = "trade_history"
    resource_requests_total.labels(resource=resource_name).inc()
    start = time.perf_counter()
    try:
        cache_key = f"quantica://trades/{symbol}/history"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        end = date.today()
        begin = end - timedelta(days=_config.TRADE_HISTORY_DAYS_DEFAULT)
        trades = await _client.get_trades_date_range(begin, end)
        filtered = [t for t in trades if t.get("symbol") == symbol]
        result = json.dumps(filtered, default=str)
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        return _error(resource_name, str(e))
    finally:
        resource_latency_seconds.labels(resource=resource_name).observe(
            time.perf_counter() - start
        )


@mcp.resource(
    "quantica://analytics/{symbol}",
    name="analytics_symbol",
    description="Analytics summary for a specific symbol (cluster and anomaly data)",
    mime_type="application/json",
)
async def analytics_symbol(symbol: str) -> str:
    """Fetch today's trades for symbol, compute analytics summary."""
    resource_name = "analytics_symbol"
    resource_requests_total.labels(resource=resource_name).inc()
    start = time.perf_counter()
    try:
        cache_key = f"quantica://analytics/{symbol}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        today = date.today()
        trades = await _client.get_trades_for_date(today)
        symbol_trades = [t for t in trades if t.get("symbol") == symbol]

        scored = [
            t for t in symbol_trades if t.get("anomaly_score") is not None
        ]

        if not scored:
            summary = {
                "symbol": symbol,
                "count": 0,
                "avg_anomaly_score": None,
                "dominant_cluster": None,
                "latest": None,
            }
        else:
            avg_score = sum(t["anomaly_score"] for t in scored) / len(scored)

            # Find dominant cluster by frequency
            cluster_counts: dict[int, int] = {}
            for t in scored:
                cid = t.get("cluster_id")
                if cid is not None:
                    cluster_counts[cid] = cluster_counts.get(cid, 0) + 1
            dominant_cluster = (
                max(cluster_counts, key=cluster_counts.get)
                if cluster_counts
                else None
            )

            latest = scored[-1]

            summary = {
                "symbol": symbol,
                "count": len(scored),
                "avg_anomaly_score": round(avg_score, 4),
                "dominant_cluster": dominant_cluster,
                "latest": latest,
            }

        result = json.dumps(summary, default=str)
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        return _error(resource_name, str(e))
    finally:
        resource_latency_seconds.labels(resource=resource_name).observe(
            time.perf_counter() - start
        )


@mcp.resource(
    "quantica://outcomes/recent",
    name="outcomes_recent",
    description="Recent trade outcomes with P&L data (last 7 days, approved only)",
    mime_type="application/json",
)
async def outcomes_recent() -> str:
    """Fetch last 7 days of trades, filter to approved with pnl_pct present."""
    resource_name = "outcomes_recent"
    resource_requests_total.labels(resource=resource_name).inc()
    start = time.perf_counter()
    try:
        cached = _cache_get("quantica://outcomes/recent")
        if cached is not None:
            return cached

        end = date.today()
        begin = end - timedelta(days=7)
        trades = await _client.get_trades_date_range(begin, end)

        outcomes = [
            t for t in trades
            if t.get("risk_approved") is True and "pnl_pct" in t
        ]

        result = json.dumps(outcomes, default=str)
        _cache_set("quantica://outcomes/recent", result)
        return result
    except Exception as e:
        return _error(resource_name, str(e))
    finally:
        resource_latency_seconds.labels(resource=resource_name).observe(
            time.perf_counter() - start
        )


@mcp.resource(
    "quantica://risk/state",
    name="risk_state",
    description="Current risk exposure state across all symbols",
    mime_type="application/json",
)
async def risk_state() -> str:
    """Compute per-symbol exposure and identify near-limit symbols."""
    resource_name = "risk_state"
    resource_requests_total.labels(resource=resource_name).inc()
    start = time.perf_counter()
    try:
        cached = _cache_get("quantica://risk/state")
        if cached is not None:
            return cached

        end = date.today()
        begin = end - timedelta(days=7)
        trades = await _client.get_trades_date_range(begin, end)

        max_exposure = _config.RISK_MAX_SYMBOL_EXPOSURE

        # Get unique symbols from approved trades
        symbols = sorted({
            t["symbol"]
            for t in trades
            if t.get("symbol") and t.get("risk_approved") is True
        })

        symbol_exposures = [
            compute_symbol_exposure(trades, sym, max_exposure)
            for sym in symbols
        ]

        # Near-limit: current_exposure > 80% of max
        threshold = max_exposure * 0.8
        near_limit = [
            e for e in symbol_exposures
            if e["current_exposure"] > threshold
        ]

        state = {
            "max_exposure": max_exposure,
            "symbols": symbol_exposures,
            "near_limit_symbols": near_limit,
            "timestamp": datetime.now(tz=_UTC).isoformat(),
        }

        result = json.dumps(state, default=str)
        _cache_set("quantica://risk/state", result)
        return result
    except Exception as e:
        return _error(resource_name, str(e))
    finally:
        resource_latency_seconds.labels(resource=resource_name).observe(
            time.perf_counter() - start
        )


@mcp.resource(
    "quantica://health",
    name="health",
    description="Pipeline health status from marketserver",
    mime_type="application/json",
)
async def health() -> str:
    """Call marketserver health endpoint and return status."""
    resource_name = "health"
    resource_requests_total.labels(resource=resource_name).inc()
    start = time.perf_counter()
    try:
        cached = _cache_get("quantica://health")
        if cached is not None:
            return cached

        details = await _client.get_health_details()
        details["checked_at"] = datetime.now(tz=_UTC).isoformat()

        result = json.dumps(details, default=str)
        _cache_set("quantica://health", result)
        return result
    except Exception as e:
        return _error(resource_name, str(e))
    finally:
        resource_latency_seconds.labels(resource=resource_name).observe(
            time.perf_counter() - start
        )
