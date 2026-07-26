# Quantica

Real-time market data pipeline: Binance WebSocket → Kafka → multi-module enrichment, ML analysis, LLM storytelling, and append-only audit log.

---

## Module Map

| Module | Language | Role | Transport (in → out) |
|---|---|---|---|
| `marketListener` | Java 21 / Spring Boot 3.5 | Binance WSS → Kafka | → Kafka `order` topic |
| `markettransformer` | Java 21 / Spring Boot 3.x | Raw trades → enriched signals | Kafka `order` → RabbitMQ `signal` fanout exchange |
| `marketanalysis` | Python 3.11 / Flask | Clustering + anomaly detection | RabbitMQ `signal.analysis` queue → RabbitMQ `analytics` topic exchange |
| `marketbard` | Python 3.11 | LLM storytelling → GitHub commits | RabbitMQ `signal.bard` queue + `analytics.bard` queue → GitHub |
| `marketappendonly` | Go 1.24 / Sarama | Append-only audit ledger | Kafka `order` → `history.log` |
| `markettrade` | Python 3.13 | Trade execution worker | RabbitMQ `signal.trade` queue → blob store |
| `marketrisk` | Python 3.13 | **Internal library** — risk cap evaluation | consumed by `markettrade` (not a runnable binary) |

### RabbitMQ Architecture

`markettransformer` publishes `SignalEvent`s to a RabbitMQ **fanout exchange** (`signal`). Each downstream consumer owns its own queue and binding — the producer declares only the exchange:
- `signal.analysis` → `marketanalysis` (declared by marketanalysis on startup)
- `signal.bard` → `marketbard` (declared by marketbard on startup)
- `signal.trade` → `markettrade` (declared by markettrade on startup)

`marketanalysis` publishes ML-enriched events (with `cluster_id` + `anomaly_score`) to a RabbitMQ **topic exchange** (`analytics`) using routing key `signal.analytics.{symbol}`.

`marketbard` subscribes to the `analytics` exchange via a single `analytics.bard` queue (routing key `signal.analytics.#`), maintaining an in-memory enrichment cache keyed by symbol. When a raw signal arrives on `signal.bard`, it is enriched from the cache before being added to the event buffer.

### Start Order

```bash
# 1. Kafka + RabbitMQ (via docker compose)
make up

# 2. marketListener (must be first — it seeds the `order` topic)
cd marketListener && mvn spring-boot:run -Dspring-boot.run.profiles=local

# 3. Any downstream module
cd markettransformer && mvn spring-boot:run -Dspring-boot.run.profiles=local
cd marketanalysis   && python run.py
cd marketbard       && python run.py
cd marketappendonly && go run cmd/server/main.go
cd markettrade      && python run.py
```

---

## Transport Schemas

### Kafka Topics

| Topic | Config key | Schema |
|---|---|---|
| `order` | hardcoded in `@KafkaListener` | `QuanticaEventIngestedEvent<BinanceStreamResponse>` JSON |

**Schema changes ripple downstream.** Changing a Kafka message type requires updating all consumers of that topic.

### RabbitMQ

| Exchange | Type | Queues | Routing key | Schema |
|---|---|---|---|---|
| `signal` | fanout | `signal.analysis`, `signal.bard`, `signal.trade` | n/a (fanout) | `SignalEvent` JSON |
| `analytics` | topic | `analytics.bard` | `signal.analytics.{symbol}` | `SignalEvent` + `cluster_id`, `anomaly_score` |

**Consumer-owned queues.** Each consumer declares and binds its own queue on startup. `markettransformer` declares only the `signal` exchange — it has no knowledge of downstream queues.

**`SignalEvent`** (markettransformer) — `symbol, eventTime, type (SignalEventType), reason, price, quantity, side, metadata`

---

## Building and Testing

**Always use `make` targets** — do not run raw `mvn`, `pytest`, or `pip` commands directly.

### Versioning (`bump.sh patch|minor|major`)

`bump.sh` versions the **runnable binaries only** — Java services and Python workers. `marketrisk` is an internal library consumed by `markettrade`; it is **not bumped by `bump.sh`** and has no independent release. Do not add it to the bump script.

```bash
# Build all modules
make build

# Test all modules
make test

# Per-module
make build-listener   && make test-listener
make build-transformer && make test-transformer
make build-bard       && make test-bard
make build-risk       && make test-risk
make build-trade      && make test-trade

# Docker
make up    # start all containers
make down  # stop and remove volumes
```

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

## Python Conventions (marketanalysis, marketbard, markettrade)

- **Module-per-concern** — `app/`, `model/`, `redis_cache/`, `apache_kafka/`, `gh/` are each a package with `__init__.py`.
- **`Config` class** in `app/config.py` reads all env vars — no inline `os.getenv` scattered through code.
- **Threading** for concurrent workers — `threading.Thread(target=..., daemon=True)`.
- **kafka-python-ng** as the Kafka client.
- **No Flask for marketbard** — it's a pure worker process; Flask is only in marketanalysis for health/monitoring endpoints.
- **Shared RabbitMQ primitives** live in `shared/rabbitmq/` — `RabbitConsumer` and `RabbitPublisher`. Consumers declare their own exchange + queue + binding on startup.

## Go Conventions (marketappendonly)

- **Sarama** for Kafka consumer.
- Simple imperative style — no frameworks.
- Entry point: `cmd/server/main.go`.

---

## Dependencies of Note

- `functionico` — internal functional library, hosted on GitHub Packages. Requires `GITHUB_TOKEN` in Maven settings for resolution.
- `marketbard` requires `OPENAI_API_KEY` and `GITHUB_TOKEN` in `.env`.
- All modules require a running Kafka cluster at `localhost:9092` (configurable via `kafka.bootstrap` for Java, env var for Python/Go).
- All Python modules that consume from RabbitMQ require `shared/` to be on the Python path (`pip install -e shared/` or via `conftest.py` path injection in tests).
