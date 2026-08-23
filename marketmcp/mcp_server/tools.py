"""MCP tool definitions for marketmcp.

Tools expose actions like querying signals by symbol/date,
fetching trade history, and retrieving risk assessments.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime, timedelta

from app.config import Config
from app.metrics import tool_latency_seconds, tool_requests_total, mcp_errors_total
from mcp_server.client import MarketServerClient
from mcp_server.server import mcp
from mcp_server.utils import compute_symbol_exposure

logger = logging.getLogger(__name__)

_config = Config()
_client = MarketServerClient(
    base_url=_config.MARKETSERVER_BASE_URL,
    max_query_days=_config.MAX_QUERY_DAYS,
)


def _instrument(tool_name: str):
    """Increment request counter for a tool."""
    tool_requests_total.labels(tool=tool_name).inc()


def _error(tool_name: str, msg: str) -> str:
    """Log and count an error, return JSON error response."""
    mcp_errors_total.labels(tool=tool_name).inc()
    logger.error("[%s] %s", tool_name, msg)
    return json.dumps({"error": msg})


def _parse_date(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)


@mcp.tool(name="query_signals", description="Query signals by symbol, date range, type, and anomaly score threshold.")
async def query_signals(
    start_date: str,
    end_date: str,
    symbol: str | None = None,
    signal_type: str | None = None,
    min_anomaly_score: float | None = None,
) -> str:
    """Fetch and filter signals within a date range."""
    tool_name = "query_signals"
    _instrument(tool_name)
    start = time.perf_counter()
    try:
        sd = _parse_date(start_date)
        ed = _parse_date(end_date)
        if sd is None or ed is None:
            return _error(tool_name, "start_date and end_date are required (YYYY-MM-DD)")

        trades = await _client.get_trades_date_range(sd, ed)

        if symbol:
            trades = [t for t in trades if t.get("symbol") == symbol]
        if signal_type:
            trades = [t for t in trades if t.get("type") == signal_type]
        if min_anomaly_score is not None:
            trades = [
                t for t in trades
                if (t.get("anomaly_score") or 0) >= min_anomaly_score
            ]

        return json.dumps(trades, default=str)
    except Exception as e:
        return _error(tool_name, str(e))
    finally:
        tool_latency_seconds.labels(tool=tool_name).observe(time.perf_counter() - start)


@mcp.tool(name="get_risk_assessment", description="Assess risk exposure for a symbol given a proposed action and quantity.")
async def get_risk_assessment(
    symbol: str,
    action: str,
    quantity: float,
) -> str:
    """Compute current exposure and headroom for a symbol."""
    tool_name = "get_risk_assessment"
    _instrument(tool_name)
    start = time.perf_counter()
    try:
        end = date.today()
        begin = end - timedelta(days=7)
        trades = await _client.get_trades_date_range(begin, end)

        max_exposure = _config.RISK_MAX_SYMBOL_EXPOSURE
        exposure = compute_symbol_exposure(trades, symbol, max_exposure)
        current_exposure = exposure["current_exposure"]
        headroom = exposure["headroom"]

        # Assess the proposed action
        proposed_delta = quantity if action.upper() == "BUY" else -quantity
        post_exposure = current_exposure + proposed_delta
        approved = post_exposure <= max_exposure

        result = {
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "current_exposure": current_exposure,
            "max_exposure": max_exposure,
            "headroom": headroom,
            "post_trade_exposure": round(post_exposure, 6),
            "approved": approved,
            "assessment": "APPROVED" if approved else "REJECTED — exceeds max exposure",
        }
        return json.dumps(result, default=str)
    except Exception as e:
        return _error(tool_name, str(e))
    finally:
        tool_latency_seconds.labels(tool=tool_name).observe(time.perf_counter() - start)


@mcp.tool(name="get_trade_history", description="Fetch trade history for a symbol over the last N days.")
async def get_trade_history(
    symbol: str | None = None,
    days_back: int = 7,
    include_outcomes: bool = True,
) -> str:
    """Return recent trade history, optionally filtered by symbol."""
    tool_name = "get_trade_history"
    _instrument(tool_name)
    start = time.perf_counter()
    try:
        end = date.today()
        begin = end - timedelta(days=days_back)
        trades = await _client.get_trades_date_range(begin, end)

        if symbol:
            trades = [t for t in trades if t.get("symbol") == symbol]

        if not include_outcomes:
            for t in trades:
                t.pop("outcome", None)
                t.pop("pnl", None)

        return json.dumps(trades, default=str)
    except Exception as e:
        return _error(tool_name, str(e))
    finally:
        tool_latency_seconds.labels(tool=tool_name).observe(time.perf_counter() - start)


@mcp.tool(name="explain_anomaly", description="Explain an anomaly by finding the matching trade and nearby signals for context.")
async def explain_anomaly(
    symbol: str,
    timestamp: str,
) -> str:
    """Find trade matching symbol+timestamp, return anomaly context."""
    tool_name = "explain_anomaly"
    _instrument(tool_name)
    start = time.perf_counter()
    try:
        # Parse timestamp to get the date for fetching
        ts = datetime.fromisoformat(timestamp)
        target_date = ts.date()

        # Fetch trades for the target day and neighbors
        dates_to_check = [
            target_date - timedelta(days=1),
            target_date,
            target_date + timedelta(days=1),
        ]
        all_trades: list[dict] = []
        for d in dates_to_check:
            all_trades.extend(await _client.get_trades_for_date(d))

        # Find the exact match
        match = None
        for t in all_trades:
            event_time = t.get("eventTime") or t.get("event_time") or t.get("timestamp")
            if t.get("symbol") == symbol and event_time == timestamp:
                match = t
                break

        if match is None:
            return _error(tool_name, f"No trade found for {symbol} at {timestamp}")

        # Find nearby signals (same symbol, within 5 minutes)
        window = timedelta(minutes=5)
        nearby: list[dict] = []
        for t in all_trades:
            if t.get("symbol") != symbol or t is match:
                continue
            event_time = t.get("eventTime") or t.get("event_time") or t.get("timestamp")
            if event_time:
                try:
                    t_ts = datetime.fromisoformat(event_time)
                    if abs(t_ts - ts) <= window:
                        nearby.append(t)
                except (ValueError, TypeError):
                    pass

        result = {
            "symbol": symbol,
            "timestamp": timestamp,
            "cluster_id": match.get("cluster_id"),
            "anomaly_score": match.get("anomaly_score"),
            "signal_type": match.get("type"),
            "price": match.get("price"),
            "quantity": match.get("quantity"),
            "nearby_signals": nearby[:10],
            "nearby_count": len(nearby),
        }
        return json.dumps(result, default=str)
    except Exception as e:
        return _error(tool_name, str(e))
    finally:
        tool_latency_seconds.labels(tool=tool_name).observe(time.perf_counter() - start)


@mcp.tool(name="get_dashboard_summary", description="Aggregate dashboard summary: signals processed, trades executed, anomalies, risk rejections.")
async def get_dashboard_summary(
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """Aggregate stats for a date range (defaults to today)."""
    tool_name = "get_dashboard_summary"
    _instrument(tool_name)
    start = time.perf_counter()
    try:
        ed = _parse_date(end_date) or date.today()
        sd = _parse_date(start_date) or ed

        trades = await _client.get_trades_date_range(sd, ed)

        signals_processed = len(trades)
        trades_executed = sum(1 for t in trades if t.get("risk_approved") is True)
        risk_rejections = sum(1 for t in trades if t.get("risk_approved") is False)

        # Top anomalies by score
        scored = [t for t in trades if t.get("anomaly_score") is not None]
        scored.sort(key=lambda t: t.get("anomaly_score", 0), reverse=True)
        top_anomalies = scored[:5]

        symbols_active = list({t.get("symbol") for t in trades if t.get("symbol")})

        result = {
            "start_date": sd.isoformat(),
            "end_date": ed.isoformat(),
            "signals_processed": signals_processed,
            "trades_executed": trades_executed,
            "risk_rejections": risk_rejections,
            "symbols_active": sorted(symbols_active),
            "symbols_active_count": len(symbols_active),
            "top_anomalies": [
                {
                    "symbol": t.get("symbol"),
                    "anomaly_score": t.get("anomaly_score"),
                    "type": t.get("type"),
                    "timestamp": t.get("eventTime") or t.get("event_time") or t.get("timestamp"),
                }
                for t in top_anomalies
            ],
        }
        return json.dumps(result, default=str)
    except Exception as e:
        return _error(tool_name, str(e))
    finally:
        tool_latency_seconds.labels(tool=tool_name).observe(time.perf_counter() - start)
