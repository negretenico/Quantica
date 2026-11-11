"""E2E helpers for marketserver: HTTP and SSE interactions."""

import json
import time
from dataclasses import dataclass

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


@dataclass
class SSEEvent:
    """A parsed Server-Sent Event."""
    event: str | None = None
    data: dict | None = None
    id: str | None = None
    retry: int | None = None


def subscribe_portfolio(
    base_url: str,
    count: int = 1,
    timeout_seconds: int = 30,
) -> list[SSEEvent]:
    """Connect to ``GET /portfolio/subscribe`` and collect *count* data events.

    Skips retry-only and keepalive frames.  Returns parsed ``SSEEvent``
    objects or raises ``TimeoutError``.
    """
    events: list[SSEEvent] = []
    deadline = time.monotonic() + timeout_seconds

    current = SSEEvent()

    with requests.get(
        f"{base_url}/portfolio/subscribe",
        stream=True,
        timeout=(5, timeout_seconds),
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if time.monotonic() > deadline:
                break

            # Empty line = end of frame
            if line == "":
                if current.data is not None:
                    events.append(current)
                    if len(events) >= count:
                        break
                current = SSEEvent()
                continue

            if line.startswith("id: "):
                current.id = line[4:]
            elif line.startswith("event: "):
                current.event = line[7:]
            elif line.startswith("data: "):
                current.data = json.loads(line[6:])
            elif line.startswith("retry: "):
                current.retry = int(line[7:])
            # Lines starting with ':' are comments (keepalives) — skip.

    if len(events) < count:
        raise TimeoutError(
            f"Only received {len(events)}/{count} SSE events within {timeout_seconds}s"
        )
    return events
