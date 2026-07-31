# markettrade

Trade execution worker. Consumes signals from the RabbitMQ `signal.trade` queue, runs a decision engine to determine actionable trades, evaluates each proposed action through the `marketrisk` risk engine, and writes approved decisions to a blob store as JSONL.

## Prerequisites

- RabbitMQ running (start from the repo root with `make up`)
- Shared library installed: `pip install -e shared/`
- Risk library installed: `pip install -e marketrisk/`
- Trade library installed: `pip install -e markettrade/`

## Running

```bash
cd markettrade && py run.py
```

The service connects to RabbitMQ, declares its own `signal.trade` queue bound to the `signal` fanout exchange, and begins consuming signals.

## Configuration

All configuration is read from environment variables via `app/config.py`. Defaults are suitable for local development against the Docker Compose stack started by `make up`.

## Blob store output

Approved decisions are written as JSONL files to the blob store path (default: `decisions/trade/`). Each line is a JSON object containing the original decision fields plus `risk_approved: true` and `sized_quantity`.

## Manual verification

1. Start infrastructure: `make up` (from repo root)
2. Start the upstream pipeline (marketListener, markettransformer) so signals flow into RabbitMQ
3. Start markettrade: `cd markettrade && py run.py`
4. Observe logs -- incoming signals produce either:
   - `Risk REJECTED` warnings (signal was actionable but failed risk checks)
   - `HOLD` debug messages (signal did not meet decision thresholds)
   - No log for approved writes (check the blob store directory)
5. Verify approved decisions landed on disk:
   ```bash
   ls decisions/trade/
   # Expect one or more .jsonl files
   # Inspect contents:
   py -c "import json, glob; [print(json.loads(l)) for f in glob.glob('decisions/trade/*.jsonl') for l in open(f)]"
   ```

## Tests

```bash
make test-trade
```
