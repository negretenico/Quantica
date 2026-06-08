# Quantica

Real-time market data pipeline: Binance WebSocket → Kafka → multi-module enrichment, ML analysis, LLM storytelling, and append-only audit log.

---

## Module Map

| Module | Language | Role | Kafka (in → out) |
|---|---|---|---|
| `marketListener` | Java 21 / Spring Boot 3.5 | Binance WSS → Kafka | → `order` |
| `markettransformer` | Java 21 / Spring Boot 3.x | Raw trades → enriched signals | `order` → `signal` |
| `marketanalysis` | Python 3.11 / Flask | Clustering + anomaly detection | `signal` → anomaly events |
| `marketbard` | Python 3.11 | LLM storytelling → GitHub commits | `signal` + `analytics` → GitHub |
| `marketappendonly` | Go 1.24 / Sarama | Append-only audit ledger | `order` → `history.log` |

### Start Order

```bash
# 1. Kafka
docker run -p 9092:9092 apache/kafka-native:4.0.0

# 2. marketListener (must be first — it seeds the `order` topic)
cd marketListener && mvn spring-boot:run -Dspring-boot.run.profiles=local

# 3. Any downstream module
cd markettransformer && mvn spring-boot:run -Dspring-boot.run.profiles=local
cd marketanalysis   && python run.py
cd marketbard       && python run.py
cd marketappendonly && go run cmd/server/main.go
```

---

## Kafka Topics & Schemas

| Topic name | Config key | Schema |
|---|---|---|
| `order` | hardcoded in `@KafkaListener` | `BinanceStreamResponse` JSON |
| configurable | `market.signal.topic` | `SignalEvent` JSON |
| configurable | `market.order.topic` | `QuanticaEventIngestedEvent<BinanceStreamResponse>` JSON |

**`SignalEvent`** (markettransformer) — `symbol, eventTime, type (SignalEventType), reason, price, quantity, side, metadata`

**Schema changes ripple downstream.** Changing a Kafka message type in one module requires updating all consumers of that topic.

---

## Java Conventions (marketListener, markettransformer)

- **Records** for all value types — `SignalEvent`, `BinanceStreamResponse` are records.
- **Lombok `@Slf4j`** for logging; no manual Logger declarations.
- **Constructor injection only** — no field `@Autowired`.
- **`@Value`** for externalized config, bound in constructors.
- **Spring internal eventing** — `ApplicationEventPublisher` + `ApplicationListener<E>` for decoupling consumers from signal detectors (see `OrderConsumer` → `AggressiveBuyerSeller`).
- **`@KafkaListener`** on consumer classes; `KafkaTemplate` injected into publisher services.
- **Kafka producer config pattern** — always use `Map.of(...)`, always set `JsonSerializer.ADD_TYPE_INFO_HEADERS, false`.
- **`functionico` library** — internal functional utilities (Result monad). Pull from GitHub Packages (`maven.pkg.github.com/negretenico/functionico`).
- **Tests** — JUnit 5 + Mockito, `@ExtendWith(MockitoExtension.class)`, no Spring context in unit tests.

## Python Conventions (marketanalysis, marketbard)

- **Module-per-concern** — `app/`, `model/`, `redis_cache/`, `apache_kafka/`, `gh/` are each a package with `__init__.py`.
- **`Config` class** in `app/config.py` reads all env vars — no inline `os.getenv` scattered through code.
- **Threading** for concurrent workers — `threading.Thread(target=..., daemon=True)`.
- **kafka-python-ng** as the Kafka client.
- **No Flask for marketbard** — it's a pure worker process; Flask is only in marketanalysis for health/monitoring endpoints.

## Go Conventions (marketappendonly)

- **Sarama** for Kafka consumer.
- Simple imperative style — no frameworks.
- Entry point: `cmd/server/main.go`.

---

## Testing

```bash
# Java modules
cd <module> && mvn test

# Python modules
cd <module> && python -m pytest

# Go
cd marketappendonly && go test ./...
```

---

## Dependencies of Note

- `functionico` — internal functional library, hosted on GitHub Packages. Requires `GITHUB_TOKEN` in Maven settings for resolution.
- `marketbard` requires `OPENAI_API_KEY` and `GITHUB_TOKEN` in `.env`.
- All modules require a running Kafka cluster at `localhost:9092` (configurable via `kafka.bootstrap` for Java, env var for Python/Go).
