---
name: java-spring
description: Use for all work inside marketListener or markettransformer — Java 21, Spring Boot, Kafka producer/consumer, Spring internal events, Lombok, Mockito tests.
---

You are working inside a Java 21 / Spring Boot 3.x module of the Quantica project.

## Modules in scope
- `marketListener` — Binance WebSocket handler, publishes raw `BinanceStreamResponse` to the `order` Kafka topic via `KafkaTemplate`. Uses `QuanticaEventIngestedEvent<T>` as the envelope type.
- `markettransformer` — Kafka consumer on `order`, fires Spring `ApplicationEvent`s internally, signal detectors implement `ApplicationListener<OrderReceived>`, publishes `SignalEvent` to the signal Kafka topic.

## Key patterns
- Records for all value/DTO types (`SignalEvent`, `BinanceStreamResponse`).
- Constructor injection only — no field `@Autowired`.
- `@Value` in constructors for externalized config.
- `@Slf4j` (Lombok) for logging.
- Kafka producer config: always `Map.of(...)`, always `JsonSerializer.ADD_TYPE_INFO_HEADERS, false`.
- Spring internal eventing: `ApplicationEventPublisher.publishEvent(...)` → `ApplicationListener<E>` — this is the decoupling boundary between the Kafka consumer and the signal detection logic.
- `functionico` lib provides Result monad and functional helpers.
- Tests: JUnit 5 + Mockito, `@ExtendWith(MockitoExtension.class)`, no Spring context load in unit tests.

## What NOT to do
- Do not use `@Autowired` on fields.
- Do not add type headers to Kafka serializers.
- Do not use mutable POJOs where records suffice.
- Do not load the full Spring context in unit tests — mock dependencies directly.
- Do not add comments to code that already clearly expresses intent.
