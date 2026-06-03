---
name: event-pipeline
description: Use when a change spans multiple modules — adding a new Kafka topic, changing an event schema, tracing an event from Binance WSS through to the final consumer, or designing a new pipeline stage.
---

You are reasoning about the full Quantica event pipeline. Your job is cross-module: schema design, topic planning, impact analysis, and data-flow tracing.

## Full pipeline

```
Binance WSS
  └─► marketListener (Java)
        └─► Kafka: order topic
              ├─► markettransformer (Java)
              │     └─► Kafka: signal topic
              │           ├─► marketanalysis (Python) → Kafka: anomaly events
              │           └─► marketbard (Python) → Redis → LLM → GitHub
              └─► marketappendonly (Go) → history.log
```

## Schema reference

| Type | Module | Fields |
|---|---|---|
| `BinanceStreamResponse` | marketListener, markettransformer | `eventType, eventTime, symbol, tradeId, price, quantity, buyerOrderId, isBuyerMarketMaker` |
| `QuanticaEventIngestedEvent<T>` | marketListener | wrapper being introduced — envelope over `BinanceStreamResponse` |
| `SignalEvent` | markettransformer | `symbol, eventTime, type (SignalEventType), reason, price, quantity, side (TradeIndicator), metadata` |
| `SignalEventType` | markettransformer | `LARGE_TRADE, DOMINANT_SIDE, PRICE_SPIKE, PRICE_DIP` |

## Rules for cross-module changes
1. Any change to a Kafka message schema must be evaluated against **all consumers of that topic** before implementation.
2. New Kafka topics should be named in kebab-case and configured via `@Value` / env var — never hardcoded (exception: `order` topic is currently hardcoded in `@KafkaListener`).
3. Java modules serialize with `JsonSerializer` (no type headers). Python consumers use `json.loads`. Go consumers use `json.Unmarshal`. All three must agree on field names.
4. Adding a new downstream module means it needs: a Kafka consumer on the appropriate topic, a `Config` class for its env vars, and a Dockerfile.

## What to produce
When asked to trace an event: show the full path from source to sink, the class/function at each hop, and the Kafka topic between hops.
When asked to design a new stage: specify the input topic, output topic (if any), schema, and which existing module pattern it most closely follows.
