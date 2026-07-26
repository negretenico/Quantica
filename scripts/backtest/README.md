# Backtest Scripts

Offline replay of the markettransformer detector logic against a Kafka topic dump.

---

## Prerequisites

- Python 3.13 (use `py` on Windows)
- A JSONL dump file produced by `scripts/dump_topic.py`

---

## Running the threshold sweep

```bash
py scripts/backtest/evaluate.py --dump-path dump/trades.jsonl
```

**With a custom output directory:**

```bash
py scripts/backtest/evaluate.py --dump-path dump/trades.jsonl --output-dir my-results/
```

**Output:** `scripts/backtest/results/threshold_sweep.csv` (or `<output-dir>/threshold_sweep.csv`)

### CSV columns

| Column | Description |
|---|---|
| `detector` | Detector name: `large_trade`, `price_spike`, `dominant_side` |
| `threshold` | The threshold value swept for this row |
| `fire_count` | Total number of signals fired across all trades |
| `fire_rate_per_1k_trades` | `fire_count / total_trades * 1000` — signals per 1,000 trades |

### Threshold ranges swept

| Detector | Parameter | Values |
|---|---|---|
| `large_trade` | quantity threshold | 100k, 250k, 500k, 750k, 1M, 2M, 5M |
| `price_spike` | % deviation from rolling avg | 0.5%, 1%, 1.5%, 2%, 3%, 5%, 10% |
| `dominant_side` | consecutive same-side streak | 3, 4, 5, 6, 7, 8, 10 |

---

## Producing a dump

If you don't have a dump yet, run `dump_topic.py` against a live Kafka cluster:

```bash
py scripts/dump_topic.py --topic order --output dump/trades.jsonl
```

---

## Running the tests

```bash
make test-backtest
```
