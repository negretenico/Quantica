"""E2E test: portfolio state via marketserver REST and SSE endpoints.

Publishes a BUY signal to the ``signal`` fanout exchange so markettrade
creates a position in ``portfolio_state.json``.  Then verifies:

1. ``GET /portfolio`` on marketserver returns the updated state.
2. ``GET /portfolio/stream`` emits an SSE event containing the position.
"""

import uuid

import pytest

from e2e.bard_helpers import publish_signal_event
from e2e.server_helpers import consume_sse_events, poll_portfolio_via_server
from e2e.trade_helpers import poll_portfolio_state


@pytest.mark.e2e
def test_portfolio_rest_endpoint(
    ensure_markettrade,
    ensure_marketserver,
    rabbitmq_url,
    portfolio_state_path,
    marketserver_url,
):
    """A BUY signal should be visible via GET /portfolio on marketserver."""

    symbol = f"E2E{uuid.uuid4().hex[:8].upper()}"

    payload = {
        "symbol": symbol,
        "type": "LARGE_TRADE",
        "eventTime": int(__import__("time").time() * 1000),
        "reason": "E2E test portfolio REST endpoint",
        "price": 42000.00,
        "quantity": 25.0,
        "side": "BUY",
        "cluster_id": 1,
        "anomaly_score": 0.85,
        "metadata": {},
    }

    publish_signal_event(rabbitmq_url, payload)

    # First wait for markettrade to write the file (file-based poll).
    poll_portfolio_state(portfolio_state_path, symbol, timeout_seconds=90)

    # Then verify marketserver serves it over HTTP.
    state = poll_portfolio_via_server(marketserver_url, symbol, timeout_seconds=30)

    assert state["cash"] < state["starting_balance"]
    assert symbol in state["positions"]
    pos = state["positions"][symbol]
    assert pos["quantity"] > 0
    assert pos["avg_entry_price"] == 42000.00
    assert "updated_at" in state


@pytest.mark.e2e
def test_portfolio_sse_emits_state(
    ensure_markettrade,
    ensure_marketserver,
    rabbitmq_url,
    portfolio_state_path,
    marketserver_url,
):
    """The SSE stream should emit an event containing the portfolio state."""

    symbol = f"E2E{uuid.uuid4().hex[:8].upper()}"

    payload = {
        "symbol": symbol,
        "type": "LARGE_TRADE",
        "eventTime": int(__import__("time").time() * 1000),
        "reason": "E2E test portfolio SSE stream",
        "price": 38000.00,
        "quantity": 30.0,
        "side": "BUY",
        "cluster_id": 3,
        "anomaly_score": 0.92,
        "metadata": {},
    }

    publish_signal_event(rabbitmq_url, payload)

    # Wait for markettrade to write portfolio_state.json with our symbol.
    poll_portfolio_state(portfolio_state_path, symbol, timeout_seconds=90)

    # Connect to the SSE stream and collect the first event.
    events = consume_sse_events(marketserver_url, count=1, timeout_seconds=30)

    assert len(events) >= 1
    state = events[0]
    assert "cash" in state
    assert "positions" in state
    assert "starting_balance" in state
    assert "updated_at" in state


@pytest.mark.e2e
def test_portfolio_sse_content_type(
    ensure_marketserver,
    marketserver_url,
):
    """The SSE endpoint should return text/event-stream content type."""
    import requests

    resp = requests.get(
        f"{marketserver_url}/portfolio/stream",
        stream=True,
        timeout=(5, 10),
    )
    assert "text/event-stream" in resp.headers.get("Content-Type", "")
    assert resp.headers.get("Cache-Control") == "no-cache"
    resp.close()


@pytest.mark.e2e
def test_portfolio_contract_fields(
    ensure_markettrade,
    ensure_marketserver,
    rabbitmq_url,
    portfolio_state_path,
    marketserver_url,
):
    """Portfolio state served by marketserver must match the contract schema."""

    symbol = f"E2E{uuid.uuid4().hex[:8].upper()}"

    payload = {
        "symbol": symbol,
        "type": "LARGE_TRADE",
        "eventTime": int(__import__("time").time() * 1000),
        "reason": "E2E test portfolio contract",
        "price": 55000.00,
        "quantity": 20.0,
        "side": "BUY",
        "cluster_id": 0,
        "anomaly_score": 0.75,
        "metadata": {},
    }

    publish_signal_event(rabbitmq_url, payload)
    poll_portfolio_state(portfolio_state_path, symbol, timeout_seconds=90)

    state = poll_portfolio_via_server(marketserver_url, symbol, timeout_seconds=30)

    # Top-level contract fields
    assert isinstance(state["cash"], (int, float))
    assert isinstance(state["starting_balance"], (int, float))
    assert isinstance(state["realized_pnl"], (int, float))
    assert isinstance(state["positions"], dict)
    assert isinstance(state["updated_at"], str)

    # Position sub-fields
    pos = state["positions"][symbol]
    assert isinstance(pos["quantity"], (int, float))
    assert isinstance(pos["avg_entry_price"], (int, float))
    assert isinstance(pos["opened_at"], str)
