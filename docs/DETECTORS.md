# Detectors

Signal detectors live in `markettransformer` and fire as Spring `ApplicationListener<OrderReceived>` components. Each detector receives every incoming trade independently and publishes a `SignalEvent` to the `signal` Kafka topic when its condition is met.

---

## [LargeTradeDetected](detectors/large-trade-detected.md)

**Signal:** `LARGE_TRADE` | **Trigger:** `quantity > 1,000,000 base units`

Fires when a single trade's raw quantity exceeds one million base units. The threshold is an outlier detection boundary — not normalized. For BTC it almost never fires (only tens of units trade at a time); for meme coins and high-supply tokens it is the primary pump detection mechanism. The same threshold deliberately asks a different question of each symbol.

**Latency:** p50 1 µs · p95 5 µs · p99 15 µs → [Full details](detectors/large-trade-detected.md)

---

## [PriceSpike](detectors/price-spike.md)

**Signal:** `PRICE_SPIKE` | **Trigger:** `|price - moving_avg| / moving_avg > 2%`

Fires when the incoming price deviates more than 2% from the 100-trade moving average for that symbol. Each symbol maintains its own independent price window. The 2% threshold is a starting point calibrated for stable-market conditions and has not been tuned against historical volatility data.

**Latency:** p50 13 µs · p95 119 µs · p99 278 µs → [Full details](detectors/price-spike.md)

---

## [AggressiveBuyerSeller](detectors/aggressive-buyer-seller.md)

**Signal:** `DOMINANT_SIDE` | **Trigger:** `5 consecutive trades on the same side`

Fires when the same trade side (BUY or SELL) appears 5 times in a row for a symbol, signalling aggressive market entry or exit pressure. Resets after each fire — so sustained one-sided flow fires again at 10, 15, 20... Trade side is taken directly from the Binance stream with no normalization. Symbols are tracked independently.

**Latency:** p50 ~1 µs · p95 ~230 µs · p99 ~400 µs → [Full details](detectors/aggressive-buyer-seller.md)
