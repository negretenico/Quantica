"""MCP prompt definitions for marketmcp.

Prompts provide pre-built templates for common pipeline queries
such as daily market summaries and anomaly investigation.
"""

from __future__ import annotations

import logging

from mcp.server.mcpserver.prompts.base import UserMessage
from mcp.types import EmbeddedResource, TextContent, TextResourceContents

from app.metrics import prompt_requests_total
from mcp_server.server import mcp

logger = logging.getLogger(__name__)


def _instrument(prompt_name: str) -> None:
    """Increment request counter for a prompt."""
    prompt_requests_total.labels(prompt=prompt_name).inc()


@mcp.prompt(
    name="market_briefing",
    description="Generate a market briefing covering recent pipeline activity, anomalies, trades, and risk warnings.",
)
async def market_briefing(hours_back: int = 24) -> list[UserMessage]:
    """Market briefing prompt covering the last N hours."""
    prompt_name = "market_briefing"
    _instrument(prompt_name)

    template = (
        f"Provide a market briefing covering the last {hours_back} hours. "
        "Include: total signals processed, notable anomalies (score > 0.9), "
        "trade decisions made, P&L summary, and any risk warnings."
    )

    return [
        UserMessage(content=TextContent(type="text", text=template)),
        UserMessage(
            content=EmbeddedResource(
                type="resource",
                resource=TextResourceContents(
                    uri="quantica://trades/latest",
                    mime_type="application/json",
                    text="",
                ),
            ),
        ),
        UserMessage(
            content=EmbeddedResource(
                type="resource",
                resource=TextResourceContents(
                    uri="quantica://outcomes/recent",
                    mime_type="application/json",
                    text="",
                ),
            ),
        ),
        UserMessage(
            content=EmbeddedResource(
                type="resource",
                resource=TextResourceContents(
                    uri="quantica://risk/state",
                    mime_type="application/json",
                    text="",
                ),
            ),
        ),
    ]


@mcp.prompt(
    name="risk_report",
    description="Summarize current risk exposure, near-limit symbols, concentration warnings, and rejected trades.",
)
async def risk_report() -> list[UserMessage]:
    """Risk report prompt summarizing current exposure and recommendations."""
    prompt_name = "risk_report"
    _instrument(prompt_name)

    template = (
        "Summarize current risk exposure. List all near-limit symbols, "
        "concentration warnings, and any rejected trades in the last hour. "
        "Recommend whether to tighten or relax limits."
    )

    return [
        UserMessage(content=TextContent(type="text", text=template)),
        UserMessage(
            content=EmbeddedResource(
                type="resource",
                resource=TextResourceContents(
                    uri="quantica://risk/state",
                    mime_type="application/json",
                    text="",
                ),
            ),
        ),
        UserMessage(
            content=EmbeddedResource(
                type="resource",
                resource=TextResourceContents(
                    uri="quantica://outcomes/recent",
                    mime_type="application/json",
                    text="",
                ),
            ),
        ),
    ]


@mcp.prompt(
    name="anomaly_investigation",
    description="Investigate why a symbol was flagged as anomalous, with cluster and scoring context.",
)
async def anomaly_investigation(symbol: str) -> list[UserMessage]:
    """Anomaly investigation prompt for a specific symbol."""
    prompt_name = "anomaly_investigation"
    _instrument(prompt_name)

    template = (
        f"Investigate why {symbol} was flagged as anomalous. "
        "Show the anomaly score, cluster assignment, distance from cluster center, "
        "and compare to recent normal signals for the same symbol."
    )

    return [
        UserMessage(content=TextContent(type="text", text=template)),
        UserMessage(
            content=EmbeddedResource(
                type="resource",
                resource=TextResourceContents(
                    uri=f"quantica://trades/{symbol}/history",
                    mime_type="application/json",
                    text="",
                ),
            ),
        ),
        UserMessage(
            content=EmbeddedResource(
                type="resource",
                resource=TextResourceContents(
                    uri=f"quantica://analytics/{symbol}",
                    mime_type="application/json",
                    text="",
                ),
            ),
        ),
    ]
