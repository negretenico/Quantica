# PriceSpike

**File:** `markettransformer/src/main/java/.../event/PriceSpike.java`
**Signal type:** `PRICE_SPIKE`

## Trigger

```
|current_price - moving_average| / moving_average > 0.02
```

Where `moving_average` is the mean of the last 100 prices for that symbol. Each symbol maintains an independent price window — there is no cross-symbol contamination.

## Threshold rationale

2% was chosen as a reasonable starting point for a stable market. In normal conditions, tick-to-tick price movement on liquid crypto pairs is well under 2%, so a deviation of that magnitude from the recent moving average is a meaningful signal. It has not been calibrated against historical volatility data and is intended as a first-pass threshold to be refined.

## Window design

The detector keeps a bounded sliding window of the last 100 prices per symbol. On each incoming trade:

1. Compute the moving average of the current window
2. Compare the incoming price to that average
3. Publish a signal if the deviation exceeds 2%
4. Add the new price to the window and evict the oldest if size exceeds 100

This means the sensitivity increases as the window fills — a single-price window behaves like a tick-to-tick comparison, while a full 100-price window smooths over short-term noise before firing.

## Known limitations

- **No false positive detection** — thin order books can produce 2% moves on small size. This is unaddressed.
- **Threshold is not symbol-normalized** — 2% on BTC and 2% on a meme coin carry different market significance. Symbols are kept independent by design; per-symbol thresholds are future work.
- **Window is count-based, not time-based** — at high tick rates the 100-price window may represent only milliseconds; at low tick rates it may span minutes. Time-bounding the window is not implemented.

## Latency budget

Instrumented with `@Timed(value = "quantica.stage.detector", extraTags = {"detector", "price_spike"})`.

| Percentile | Latency |
|---|---|
| p50 | 13 µs |
| p95 | 119 µs |
| p99 | 278 µs |

Higher than `LargeTradeDetected` due to the moving average computation over the window on every tick. Pipeline-level lag is documented in [`docs/PERFORMANCE.md`](../PERFORMANCE.md).

## Backtest

**Dump:** `dump/order_20260723_1Hours.jsonl` (362,129 trades, 2026-07-23, 1 hour)
**Sweep script:** `scripts/backtest/evaluate.py`
**Results:** `scripts/backtest/results/threshold_sweep.csv`

| Threshold (% deviation) | Fire count | Fire rate / 1k trades |
|---|---|---|
| 0.5% | 74,022 | 204.41 |
| 1.0% | 71,084 | 196.29 |
| 1.5% | 23,029 | 63.59 |
| 2.0% _(current)_ | 23,029 | 63.59 |
| 3.0% | 7,013 | 19.37 |
| 5.0% | 1,404 | 3.88 |
| 10.0% | 1,036 | 2.86 |

The 1.5% and 2.0% thresholds produced identical fire counts — no events in this dump fell in the 1.5%–2.0% deviation band. The largest sensitivity cliff is between 1.0% (196/1k) and 1.5% (64/1k).
