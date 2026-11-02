"""E2E test: signal exchange -> markettrade -> trade decision blob.

Publishes an enriched SignalEvent to the ``signal`` fanout exchange
with a unique symbol.  markettrade consumes it from the ``signal.trade``
queue, runs decision + risk evaluation, and writes an approved decision
to ``decisions/trade/decisions_YYYY-MM-DD.jsonl``.

The test polls the host-mapped blob directory until the record appears.
"""

import uuid

import pytest

from e2e.bard_helpers import publish_signal_event
from e2e.trade_helpers import poll_trade_blob


@pytest.mark.e2e
def test_enriched_signal_produces_trade_blob(
    ensure_markettrade,
    rabbitmq_url,
    trade_blob_dir,
):
    """An enriched signal published to the signal exchange should produce a trade decision blob."""

    symbol = f"E2E{uuid.uuid4().hex[:8].upper()}"

    # Build a payload that will pass validation, decision (BUY), and risk checks.
    # - anomaly_score > ANOMALY_SCORE_THRESHOLD (0.3) → not HOLD
    # - type LARGE_TRADE → BUY action
    # - quantity 50 < MAX_TRADE_QUANTITY (100) → risk approved
    payload = {
        "symbol": symbol,
        "type": "LARGE_TRADE",
        "eventTime": int(__import__("time").time() * 1000),
        "reason": "E2E test large trade signal",
        "price": 50000.00,
        "quantity": 50.0,
        "side": "BUY",
        "cluster_id": 2,
        "anomaly_score": 0.9,
        "metadata": {},
    }

    # Publish to the signal fanout exchange (where markettrade consumes from).
    publish_signal_event(rabbitmq_url, payload)

    # Poll the host-mapped blob directory for the decision record.
    record = poll_trade_blob(trade_blob_dir, symbol, timeout_seconds=30)

    # Validate the decision blob fields.
    assert record["symbol"] == symbol
    assert record["action"] == "BUY"
    assert record["entry_price"] == 50000.00
    assert record["signal_type"] == "LARGE_TRADE"
    assert record["risk_approved"] is True
    assert record["sized_quantity"] > 0
    assert "timestamp_utc" in record
    assert record["cluster_id"] == 2
    assert record["anomaly_score"] == 0.9
