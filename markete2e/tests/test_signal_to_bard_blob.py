"""E2E test: signal exchange -> marketbard -> bard story blob.

Publishes signal events to the ``signal`` fanout exchange with a unique
symbol.  marketbard consumes them on ``signal.bard``, buffers them,
runs a window summary (fake LLM), then a synthesis (fake LLM), and
writes the narrative to ``decisions/bard/decisions_YYYY-MM-DD.jsonl``.

The test polls the host-mapped blob directory until the record appears.

Requires ``MODEL_BACKEND=fake`` and ``SYNTHESIS_DELAY_SECONDS=90`` in
the marketbard container (set via docker-compose.test.yaml).
"""

import time
import uuid
from datetime import datetime

import pytest

from e2e.bard_helpers import poll_bard_blob, publish_signal_event

E2E_FAKE_MARKER = "[E2E_FAKE]"


@pytest.mark.e2e
def test_signal_produces_bard_blob(
    ensure_marketbard,
    rabbitmq_url,
    bard_blob_dir,
):
    """Signal events on the fanout exchange should produce a bard story blob."""

    symbol = f"E2E{uuid.uuid4().hex[:8].upper()}"

    payload = {
        "symbol": symbol,
        "type": "LARGE_TRADE",
        "eventTime": int(time.time() * 1000),
        "reason": "E2E test bard signal",
        "price": 50000.00,
        "quantity": 500.0,
        "side": "BUY",
        "metadata": {},
    }

    # Publish several events with unique eventTimes to survive dedup.
    for i in range(3):
        payload["eventTime"] = int(time.time() * 1000) + i
        publish_signal_event(rabbitmq_url, payload)

    # Poll for the bard blob.
    # Timeline: window fires at ~60s, synthesis at ~90s, write shortly after.
    record = poll_bard_blob(bard_blob_dir, marker=E2E_FAKE_MARKER, timeout_seconds=150)

    assert "content" in record
    assert E2E_FAKE_MARKER in record["content"]
    assert "written_at" in record
    # Validate ISO 8601 timestamp
    datetime.fromisoformat(record["written_at"])
