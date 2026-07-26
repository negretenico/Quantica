# Quantica

Real-time market data pipeline: Binance WebSocket → Kafka → multi-module enrichment, ML analysis, LLM storytelling, and append-only audit log.

---

## Module Map

| Module | Language | Role | Transport (in → out) |
|---|---|---|---|
| `marketListener` | Java 21 / Spring Boot 3.5 | Binance WSS → Kafka | → Kafka `order` topic |
| `markettransformer` | Java 21 / Spring Boot 3.x | Raw trades → enriched signals | Kafka `order` → RabbitMQ `signal` fanout exchange |
| `marketanalysis` | Python 3.11 / Flask | Clustering + anomaly detection | RabbitMQ `signal.analysis` queue → RabbitMQ `analytics` topic exchange |
| `marketbard` | Python 3.11 | LLM storytelling → GitHub commits | RabbitMQ `signal.bard` queue + polls `analytics.bard.{symbol}` queues → GitHub |
| `marketappendonly` | Go 1.24 / Sarama | Append-only audit ledger | Kafka `order` → `history.log` |
| `markettrade` | Python 3.13 | Trade execution worker (skeleton) | RabbitMQ `signal.trade` → blob store |

### Fanout Architecture

`markettransformer` publishes `SignalEvent`s to a RabbitMQ **fanout exchange** (`signal`), which fans out to two durable queues:
- `signal.analysis` → consumed by `marketanalysis`
- `signal.bard` → consumed by `marketbard` (raw signal context)

`marketanalysis` publishes ML-enriched events (with `cluster_id` + `anomaly_score`) to a RabbitMQ **topic exchange** (`analytics`) using routing key `signal.analytics.{symbol}`. `marketbard` declares per-symbol queues (`analytics.bard.{symbol}`) bound to this exchange and polls them to enrich each raw signal before narrating.

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

## Transport Schemas

### Kafka Topics

| Topic | Config key | Schema |
|---|---|---|
| `order` | hardcoded in `@KafkaListener` | `QuanticaEventIngestedEvent<BinanceStreamResponse>` JSON |

**Schema changes ripple downstream.** Changing a Kafka message type requires updating all consumers of that topic.

### RabbitMQ

| Exchange | Type | Queues / routing keys | Schema |
|---|---|---|---|
| `signal` | fanout | `signal.analysis`, `signal.bard` | `SignalEvent` JSON |
| `analytics` | topic | `signal.analytics.{symbol}` → `analytics.bard.{symbol}` | `SignalEvent` + `cluster_id`, `anomaly_score` |

**`SignalEvent`** (markettransformer) — `symbol, eventTime, type (SignalEventType), reason, price, quantity, side, metadata`

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
