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

### Known limitation

The threshold is static and symbol-agnostic by design, but this means the detector is effectively calibrated for high-supply tokens. For BTC it functions as a near-never-fires sanity check rather than a practical signal. Future work could introduce a per-symbol threshold map if BTC-scale detection becomes a requirement.

### Latency budget

The detector is instrumented with `@Timed(value = "quantica.stage.detector", extraTags = {"detector", "large_trade_detected"})`.

In-process latency from `onApplicationEvent()` entry to `SignalPublisher.publish()` call:

| Percentile | Latency |
|---|---|
| p50 | 1 µs |
| p95 | 5 µs |
| p99 | 15 µs |

Note: this measures only the in-process detection slice. Full end-to-end latency (Binance `E` timestamp → Kafka ingestion → `OrderReceived` event → signal published) includes Kafka consumer lag. Pipeline-level lag measurements under load are documented in [`PERFORMANCE.md`](PERFORMANCE.md) — at 10x replay rate, peak consumer lag was ~270 messages and drained to 0.
