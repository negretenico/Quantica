# Quantica Pipeline — Throughput Baseline

**Date:** 2026-07-20
**Hardware:** AMD Ryzen 5 3600X 6-Core, 32 GB RAM, Windows 10
**Dump:** `dump/order_20260720_1Hours.jsonl` — 85,548 messages, 1 hour of Binance `order` topic
**Stack under test:** `markettransformer` (`market-transformer-group`) + `marketanalysis` + `marketbard` — full pipeline running normally
**Method:** `scripts/replay_topic.py` produced the dump into the live `order` topic at each speed multiplier while polling Kafka consumer lag and RabbitMQ queue depth every second.

---

## Results

| Speed | Messages | Wall time | Target time | Producer drift | Peak Kafka lag | Peak RabbitMQ depth | Lag bounded? |
|-------|----------|-----------|-------------|----------------|----------------|---------------------|--------------|
| 10x   | 85,548   | 367s      | 342s        | +7.5%          | 899            | 32                  | Yes          |
| 50x   | 85,548   | 91s       | 68s         | +33.0%         | 667            | 5                   | Yes          |
| 100x  | 85,548   | 57s       | 34s         | +67.5%         | 760            | 47                  | Yes          |

---

## Inflection Point

**Not reached.** At all three speeds, both Kafka consumer lag and RabbitMQ queue depth spiked during burst windows and drained back to zero. The pipeline never fell permanently behind.

At 100x the producer drift reached +67.5%, meaning the replay script itself could not achieve true 100x throughput — Windows `time.sleep()` has a ~1ms minimum resolution, making sub-millisecond inter-event delays impossible. The effective replay rate at "100x" was closer to **~62x**. The pipeline's actual ceiling remains above what this machine can produce.

---

## Observations

**10x (+7.5% drift)**
Kafka lag peaked at 899 and drained cleanly. RabbitMQ briefly hit 32 messages across all queues then returned to 0. The pipeline handled 10x live rate with no strain. Producer timing was accurate — +7.5% drift is within OS scheduling noise.

**50x (+33.0% drift)**
Kafka lag peaked at 667, RabbitMQ at 5. Both drained. Producer drift climbed to +33%, meaning the effective rate was closer to 37x. The consumer kept up throughout. No signs of a ceiling.

**100x (+67.5% drift)**
RabbitMQ peaked at 47 messages briefly (~msg 13,000) when Kafka lag also peaked at 701 — the one moment where downstream processing visibly felt the burst. Both drained within seconds. Effective replay rate was ~62x due to Windows timer resolution. Test is inconclusive for the pipeline above ~62x.

---

## RabbitMQ Queue Breakdown

Three queues monitored (`signal.analysis`, `signal.bard`, `analytics.bard.BTCUSDT`). Depth reported is the sum across all queues. Queues stayed near-zero at 10x and 50x. The brief spike to 47 at 100x was transient and self-correcting.

---

## Next Steps to Find the True Ceiling

To find where lag goes non-linear, the replay needs to outpace the consumer — which hasn't happened yet. Options:

1. **Flat produce loop** — remove inter-event delays entirely and produce all 85,548 messages as fast as Kafka accepts them, then watch how long it takes lag to drain. This bypasses the Windows sleep resolution problem.
2. **Run from Linux** — `time.sleep()` on Linux has microsecond resolution, enabling accurate 100x+ replay.
3. **Watch Grafana during replay** — `quantica.stage.kafka.consume` p99 in Grafana will show where per-message processing time degrades before lag goes non-linear.
