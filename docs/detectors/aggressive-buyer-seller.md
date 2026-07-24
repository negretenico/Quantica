# AggressiveBuyerSeller

**File:** `markettransformer/src/main/java/.../event/AggressiveBuyerSeller.java`
**Signal type:** `DOMINANT_SIDE`

## Trigger

```
5 consecutive trades on the same side (BUY or SELL)
```

Each symbol maintains its own independent streak counter. There is no cross-symbol contamination — a BUY streak on DOGE has no bearing on ETH, by design.

## What it detects

Repeated same-side orders signal that participants are aggressively entering or exiting the market on one side. A streak of buys suggests accumulation pressure; a streak of sells suggests distribution or exit. At 5 consecutive trades the signal is strong enough to be worth surfacing downstream.

## Streak threshold rationale

5 was chosen as a starting point. In a balanced market, the probability of 5 consecutive same-side trades by chance decreases rapidly, making it a reasonable first-pass filter without being so high that real momentum events are missed.

## Reset behavior

After the signal fires at streak=5, the counter resets to 0. If the same side continues, the detector fires again at 10 consecutive trades, then 15, and so on. This means sustained one-sided pressure produces repeated signals at every 5-trade interval rather than firing once and going silent.

## Side determination

Trade side is taken directly from the Binance stream with no normalization. Whatever Binance reports is what gets checked. The Binance `m` (maker) field is used as the proxy for taker aggression — a `false` value means the taker was the buyer; `true` means the taker was the seller. This is a Binance-specific convention and is not validated or adjusted.

## Symbol independence

Symbols are intentionally isolated. Market-moving events (e.g. a public statement about DOGE) affect individual tokens, not the broader market uniformly. Keeping symbol counters independent means a streak on one symbol cannot mask or inflate a streak on another.

## Known limitations

- **Streak threshold is static** — 5 is a starting point, not calibrated against historical order flow data.
- **No normalization of trade size** — a streak of 5 micro-trades and a streak of 5 whale trades produce the same signal. Size is not factored in.

## Latency budget

Instrumented with `@Timed(value = "quantica.stage.detector", extraTags = {"detector", "aggressive_buyer_seller"})`.

| Percentile | Latency |
|---|---|
| p50 | ~1 µs |
| p95 | ~230 µs |
| p99 | ~400 µs |

The wide p50→p99 spread reflects the ConcurrentHashMap contention under multi-symbol load. Pipeline-level lag is documented in [`docs/PERFORMANCE.md`](../PERFORMANCE.md).
