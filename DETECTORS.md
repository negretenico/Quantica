# Detectors

Signal detectors live in `markettransformer` and are implemented as Spring `ApplicationListener<OrderReceived>` components. Each detector receives every incoming trade event and decides independently whether to publish a `SignalEvent` to the `signal` Kafka topic.

---

## LargeTradeDetected

**File:** `markettransformer/src/main/java/.../event/LargeTradeDetected.java`
**Signal type:** `LARGE_TRADE`

### Trigger

```
quantity > 1,000,000 base units
```

Where `quantity` is the raw value from the Binance trade stream — no normalization applied.

### Threshold rationale

The 1,000,000 threshold is an **outlier detection boundary**, not a normalized metric. The key design insight is that the same absolute threshold carries different sensitivity depending on the symbol:

- **BTC:** typical single-trade size is on the order of tens of units. A 1M-unit BTC order is effectively impossible under normal market conditions, so this threshold almost never fires. That is intentional — high specificity means when it does fire, it means something.
- **Meme coins / high-supply tokens (e.g. DOGE-like):** 1M units is achievable in a single aggressive accumulation order. This is the primary use case — detecting pump participants moving large size in a single trade.

The differential sensitivity per symbol is not a bug or an oversight. It is the core of the algorithm: the same threshold asks a different question of each symbol based on that symbol's natural unit economics. A signal on BTC means something categorically different from the same signal on a meme coin, and the threshold respects that without requiring explicit per-symbol configuration.

### Known limitations

The threshold is static and symbol-agnostic by design, but this means the detector is effectively calibrated for high-supply tokens. For BTC it functions as a near-never-fires sanity check rather than a practical signal. Future work could introduce a per-symbol threshold map if BTC-scale detection becomes a requirement.

---

## PriceSpike

**File:** `markettransformer/src/main/java/.../event/PriceSpike.java`
**Signal type:** `PRICE_SPIKE`

### Trigger

```
|current_price - moving_average| / moving_average > 0.02
```

Where `moving_average` is the mean of the last 100 prices for that symbol. Each symbol maintains an independent price window — there is no cross-symbol contamination.

### Threshold rationale

2% was chosen as a reasonable starting point for a stable market. In normal conditions, tick-to-tick price movement on liquid crypto pairs is well under 2%, so a deviation of that magnitude from the recent moving average is a meaningful signal. It has not been calibrated against historical volatility data and is intended as a first-pass threshold to be refined.

### Window design

The detector keeps a bounded sliding window of the last 100 prices per symbol. On each incoming trade:

1. Compute the moving average of the current window
2. Compare the incoming price to that average
3. Publish a signal if the deviation exceeds 2%
4. Add the new price to the window and evict the oldest if size exceeds 100

This means the sensitivity increases as the window fills — a single-price window behaves like a tick-to-tick comparison, while a full 100-price window smooths over short-term noise before firing.

### Known limitations

- **No false positive detection** — thin order books can produce 2% moves on small size. This is unaddressed.
- **Threshold is not symbol-normalized** — 2% on BTC and 2% on a meme coin carry different market significance. Symbols are kept independent by design; per-symbol thresholds are future work.
- **Window is count-based, not time-based** — at high tick rates the 100-price window may represent only milliseconds; at low tick rates it may span minutes. Time-bounding the window is not implemented.

### Latency budget

Instrumented with `@Timed(value = "quantica.stage.detector", extraTags = {"detector", "price_spike"})`.

| Percentile | Latency |
|---|---|
| p50 | 13 µs |
| p95 | 119 µs |
| p99 | 278 µs |

Higher than `LargeTradeDetected` due to the moving average computation over the window on every tick. End-to-end pipeline lag is documented in [`PERFORMANCE.md`](PERFORMANCE.md).

