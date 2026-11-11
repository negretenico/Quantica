"""E2E helpers for marketserver: HTTP and SSE interactions."""

import json
import time

import requests


def get_portfolio(base_url: str) -> dict:
    """Fetch the current portfolio state from marketserver.

    Returns the parsed JSON or raises on non-200 status.
    """
    resp = requests.get(f"{base_url}/portfolio", timeout=10)
    resp.raise_for_status()
    return resp.json()


def poll_portfolio_via_server(
    base_url: str,
    symbol: str,
    timeout_seconds: int = 30,
    poll_interval: float = 1.0,
) -> dict:
    """Poll the ``GET /portfolio`` endpoint until a position for *symbol* exists.

    Returns the full portfolio state dict or raises ``TimeoutError``.
    """
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            data = get_portfolio(base_url)
            if symbol in data.get("positions", {}):
                return data
        except (requests.RequestException, ValueError):
            pass
        time.sleep(poll_interval)
    raise TimeoutError(
        f"No portfolio position for '{symbol}' via {base_url}/portfolio within {timeout_seconds}s"
    )


def consume_sse_events(
    base_url: str,
    count: int = 1,
    timeout_seconds: int = 30,
) -> list[dict]:
    """Connect to the ``GET /portfolio/stream`` SSE endpoint and collect *count* events.

    Returns a list of parsed JSON payloads or raises ``TimeoutError``
    if fewer than *count* events arrive within the timeout.
    """
    events = []
    deadline = time.monotonic() + timeout_seconds

    with requests.get(
        f"{base_url}/portfolio/stream",
        stream=True,
        timeout=(5, timeout_seconds),
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if time.monotonic() > deadline:
                break
            if line and line.startswith("data: "):
                payload = json.loads(line[len("data: "):])
                events.append(payload)
                if len(events) >= count:
                    break

    if len(events) < count:
        raise TimeoutError(
            f"Only received {len(events)}/{count} SSE events within {timeout_seconds}s"
        )
    return events
