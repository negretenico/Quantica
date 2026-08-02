# Quantica Hardening PRDs

Six workstreams to take the pipeline from "works on the happy path" to "production-trustworthy."

---

## PRD 1: Resilience — No Silent Message Loss

### Problem Statement

The shared RabbitMQ consumer (`shared/rabbitmq/consumer.py`) nacks failed messages with `requeue=False`, which silently drops them. There are no dead-letter queues, no retry-with-backoff, and no error handlers that preserve failed messages for inspection. On the Kafka side, `marketappendonly` and `markettransformer` lack equivalent safeguards. A single malformed event or transient downstream failure results in permanent data loss with only a log line as evidence.

### Success Criteria

- Zero messages silently dropped under normal or degraded operation.
- Failed messages land in a DLQ with full context (original payload, error, timestamp, attempt count).
- Transient failures retry with exponential backoff (configurable max retries, default 3).
- DLQ depth is exposed as a Prometheus metric and alerted on in Grafana.
- Existing unit tests pass; new tests cover retry and DLQ paths.

### Scope Boundaries

- **In scope:** RabbitMQ consumers (shared library + all Python workers), Kafka consumers (Java + Go).
- **Out of scope:** Message replay tooling, DLQ reprocessing automation (future workstream).

### Key Deliverables

1. DLQ exchange + queue declaration in `shared/rabbitmq/consumer.py`.
2. Retry-with-backoff wrapper (configurable max retries, base delay).
3. Per-module error handler that publishes to DLQ on exhausted retries.
4. Kafka `ErrorHandler` bean in `markettransformer` and `marketListener`.
5. Go-side DLQ/retry in `marketappendonly`.
6. Prometheus counters: `messages_retried_total`, `messages_dlq_total`.
7. Grafana panel for DLQ depth.

---

## PRD 2: Observability — Instrument Blind Modules

### Problem Statement

`prometheus.yml` only scrapes four of nine modules (marketlistener, markettransformer, markettrade, marketbard). `marketanalysis`, `marketappendonly`, `marketserver`, `marketnotify`, and `marketui` are invisible. `marketanalysis` has no `prometheus_client` integration at all despite being a Flask app. Grafana dashboards have not been audited for coverage against the full module set. The result: pipeline health is partially observable at best.

### Success Criteria

- `prometheus.yml` scrapes every module that exposes metrics (all Python workers, both Java services, Go service).
- `marketanalysis` exposes `prometheus_client` metrics on port 8000 (events consumed, clusters computed, anomalies detected, processing latency).
- `marketappendonly` exposes Go Prometheus metrics (events appended, append latency, errors).
- `marketserver` exposes request count/latency metrics.
- `marketnotify` exposes notification send count/error metrics.
- Grafana has one "Pipeline Health" dashboard with panels for every module's key counters/histograms.
- `make info` output includes Prometheus/Grafana URLs.

### Scope Boundaries

- **In scope:** Prometheus instrumentation, prometheus.yml, Grafana dashboard provisioning.
- **Out of scope:** Alertmanager rules, PagerDuty/Slack alert routing, distributed tracing (Jaeger/OpenTelemetry).

### Key Deliverables

1. `app/metrics.py` in `marketanalysis` with standard counters/histograms.
2. Prometheus metrics endpoint in `marketappendonly` (Go `promhttp`).
3. Prometheus metrics endpoint in `marketserver`.
4. Prometheus metrics endpoint in `marketnotify`.
5. Updated `prometheus/prometheus.yml` with all scrape targets.
6. Grafana "Pipeline Health" dashboard JSON provisioned via `grafana/provisioning/dashboards/`.
7. Verify existing `markettrade` and `marketbard` metrics are scraped correctly.

---

## PRD 3: Trade Validation — Input Validation, Price Sanity, Rate Limiting

### Problem Statement

`markettrade` accepts any dict from RabbitMQ and passes it to `decide()`. The only validation is a check for required field presence — there is no type validation, no price sanity check (negative prices, zero prices, prices wildly outside recent range), no rate limiting on trade decisions per symbol. A burst of garbage data or a Binance API glitch producing `price: "0.00"` would flow through to trade execution unchecked.

### Success Criteria

- Input schema validation rejects malformed events before they reach `decide()`.
- Price sanity: reject prices <= 0, reject prices that deviate more than N% from a trailing window (configurable, default 50%).
- Rate limiting: max N trade decisions per symbol per minute (configurable, default 10).
- All rejections are logged with reason and counted via Prometheus.
- Rejected events are nacked to DLQ (ties into PRD 1).
- Existing `test_decision.py` tests still pass; new tests cover validation and rate limiting.

### Scope Boundaries

- **In scope:** `markettrade` input pipeline only.
- **Out of scope:** Upstream validation in `markettransformer` or `marketanalysis` (desirable but separate). Replay/backfill of rejected events.

### Key Deliverables

1. `trade/validation.py` — schema validation (types, ranges), price sanity check, rate limiter.
2. Price trailing-window tracker (simple in-memory dict of recent prices per symbol).
3. Rate limiter (token bucket or sliding window per symbol).
4. Integration into `run.py` handler — validate before `decide()`.
5. Prometheus counters: `trade_validation_rejected_total{reason}`, `trade_rate_limited_total`.
6. Unit tests for each validation rule.

---

## PRD 4: Trade Outcome Tracking and Confidence Calibration

### Problem Statement

`markettrade` produces BUY/SELL/HOLD decisions with an `anomaly_score` that functions as implicit confidence, but there is no mechanism to evaluate whether those decisions were correct after the fact. Without outcome tracking, the pipeline has no feedback loop — the model could be systematically wrong and no one would know. Confidence calibration (do events with 0.9 anomaly score actually result in profitable trades 90% of the time?) is impossible without ground truth.

### Success Criteria

- Every BUY/SELL decision is recorded with its entry price and timestamp.
- A periodic evaluator checks the price at T+1m, T+5m, T+15m after each decision and records the outcome (profit/loss amount and direction correctness).
- Calibration metrics are computed: for each anomaly score bucket (0.7-0.8, 0.8-0.9, 0.9-1.0), what percentage of trades were directionally correct?
- Alert when calibration drifts: if accuracy in any bucket drops below a configurable threshold (default 40%) over a rolling window, emit a Prometheus alert metric.
- Alert when calibration is suspiciously good: if accuracy exceeds 85% consistently, flag for overfitting review.
- Outcome data is persisted to blob store for historical analysis.

### Scope Boundaries

- **In scope:** Outcome recording, price lookback, calibration computation, Prometheus metrics, blob persistence.
- **Out of scope:** Automatic model retraining, parameter tuning based on outcomes (future ML feedback loop). Real P&L tracking (this tracks directional correctness, not actual portfolio value).

### Key Deliverables

1. `trade/outcome.py` — OutcomeTracker class that records decisions and evaluates them after configurable delay windows.
2. Price lookback mechanism — poll Binance REST API (or use cached recent prices from `marketListener` data) for T+N price checks.
3. `trade/calibration.py` — CalibrationEngine that buckets outcomes by anomaly score and computes accuracy rates.
4. Blob persistence of outcome records (`decisions/outcomes/` directory).
5. Prometheus gauges: `trade_calibration_accuracy{bucket}`, `trade_outcome_correct_total`, `trade_outcome_incorrect_total`.
6. Alert-condition metric: `trade_calibration_drift` (1 when any bucket is out of expected range).
7. Unit tests for outcome evaluation logic, calibration bucketing, and drift detection.

---

## PRD 5: Risk Observability and Suspicious Position Detection

### Problem Statement

`marketrisk` enforces hard caps (per-trade quantity, per-symbol exposure, portfolio drawdown) but provides zero visibility into the risk landscape. There is no way to see how close positions are to their limits, no detection of patterns that are technically within caps but suspicious (e.g., a single symbol repeatedly hitting 95% of its exposure cap, or multiple correlated symbols all near their limits simultaneously suggesting concentration risk). The risk engine is a black box with a binary approved/rejected output.

### Success Criteria

- Every risk evaluation is instrumented with Prometheus metrics: approval rate, rejection rate by reason, sized quantity distribution.
- Near-limit detection: flag positions where current exposure exceeds N% of the cap (configurable, default 80%).
- Concentration detection: alert when more than M symbols (configurable, default 3) are simultaneously above the near-limit threshold.
- Pattern detection: flag when a symbol has been approved N times in a row without any sells (configurable, default 10) — suggests one-directional accumulation.
- All suspicious patterns are logged to a dedicated `decisions/risk-alerts/` blob store for manual review.
- Grafana panel showing risk utilization heatmap (symbol vs. exposure percentage).

### Scope Boundaries

- **In scope:** Instrumentation of `RiskEngine.evaluate()`, suspicious pattern detection, alerting metrics, blob persistence.
- **Out of scope:** Automatic cap adjustment, correlation analysis between symbols (future ML workstream), real-time position management UI.

### Key Deliverables

1. `marketrisk/risk/observer.py` — RiskObserver class that wraps or decorates `RiskEngine` to track evaluation history.
2. Near-limit detector: checks exposure / cap ratio after each evaluation.
3. Concentration detector: maintains a view of all symbols' exposure ratios, alerts on clustered near-limits.
4. Accumulation detector: tracks consecutive same-direction approvals per symbol.
5. Blob persistence to `decisions/risk-alerts/` with structured JSON (symbol, pattern type, current state, timestamp).
6. Prometheus metrics: `risk_evaluations_total{result}`, `risk_near_limit_total{symbol}`, `risk_concentration_alerts_total`, `risk_accumulation_alerts_total`.
7. Grafana "Risk Health" dashboard panel.
8. Unit tests for each detector with edge cases (exactly at threshold, reset on sell, etc.).

---

## PRD 6: End-to-End Integration Tests

### Problem Statement

All existing tests are unit tests that mock infrastructure. There are no integration tests that verify the actual message flow: Kafka topic -> Java consumer -> RabbitMQ exchange -> Python consumer -> blob store. A breaking change in a Kafka schema, a RabbitMQ routing key typo, or a blob path mismatch would only be caught in production. The docker-compose stack exists but is never exercised by CI.

### Success Criteria

- A test suite that starts the docker-compose stack, publishes a known event to Kafka, and asserts that:
  - `markettransformer` produces a `SignalEvent` on the RabbitMQ `signal` exchange.
  - `marketanalysis` produces an enriched event on the `analytics` exchange.
  - `markettrade` writes a decision blob to disk.
  - `marketbard` writes a story blob to disk.
  - `marketappendonly` appends to `history.log`.
- Tests run in CI on a schedule (not on every push — too slow).
- Test execution time < 3 minutes.
- Tests are idempotent and clean up after themselves.

### Scope Boundaries

- **In scope:** Docker-compose-based integration tests, CI workflow, test fixtures.
- **Out of scope:** Performance/load testing (separate workstream), chaos testing, testing against real Binance WebSocket.

### Key Deliverables

1. `tests/e2e/` directory with pytest-based integration tests.
2. `docker-compose.test.yaml` overlay that configures test-specific settings (shorter timeouts, known test data).
3. Test helper that publishes a known `BinanceStreamResponse` JSON to the `order` Kafka topic.
4. Assertions for each downstream module's output.
5. `Makefile` target: `make test-e2e`.
6. GitHub Actions workflow: `e2e.yml` — runs on schedule (nightly) and on-demand.
7. Cleanup script that tears down containers and removes test artifacts.

---

## Issue Breakdown

### Workstream 1: Resilience

| # | Issue Title | Labels | Blocked By |
|---|---|---|---|
| 1.1 | Add DLQ exchange and queue to shared RabbitMQ consumer | track:resilience, parallel-safe | — |
| 1.2 | Add retry-with-exponential-backoff to shared RabbitMQ consumer | track:resilience, parallel-safe | — |
| 1.3 | Wire DLQ + retry into markettrade, marketbard, marketanalysis, marketnotify consumers | track:resilience, sequential | 1.1, 1.2 |
| 1.4 | Add Kafka ErrorHandler to markettransformer and marketListener | track:resilience, parallel-safe | — |
| 1.5 | Add DLQ/retry to marketappendonly Go Kafka consumer | track:resilience, parallel-safe | — |
| 1.6 | Add Prometheus metrics for retries and DLQ depth | track:resilience, sequential | 1.3, 1.4, 1.5 |
| 1.7 | Add Grafana DLQ depth panel | track:resilience, sequential | 1.6 |

### Workstream 2: Observability

| # | Issue Title | Labels | Blocked By |
|---|---|---|---|
| 2.1 | Add prometheus_client instrumentation to marketanalysis | track:observability, parallel-safe | — |
| 2.2 | Add Prometheus metrics endpoint to marketappendonly | track:observability, parallel-safe | — |
| 2.3 | Add Prometheus metrics endpoint to marketserver | track:observability, parallel-safe | — |
| 2.4 | Add Prometheus metrics endpoint to marketnotify | track:observability, parallel-safe | — |
| 2.5 | Update prometheus.yml to scrape all modules | track:observability, sequential | 2.1, 2.2, 2.3, 2.4 |
| 2.6 | Create Grafana "Pipeline Health" dashboard | track:observability, sequential | 2.5 |

### Workstream 3: Trade Validation

| # | Issue Title | Labels | Blocked By |
|---|---|---|---|
| 3.1 | Add input schema validation to markettrade | track:validation, parallel-safe | — |
| 3.2 | Add price sanity check with trailing window | track:validation, parallel-safe | — |
| 3.3 | Add per-symbol rate limiter to markettrade | track:validation, parallel-safe | — |
| 3.4 | Wire validation pipeline into markettrade run.py handler | track:validation, sequential | 3.1, 3.2, 3.3 |
| 3.5 | Add Prometheus metrics for validation rejections | track:validation, sequential | 3.4 |

### Workstream 4: Trade Outcome Tracking and Confidence Calibration

| # | Issue Title | Labels | Blocked By |
|---|---|---|---|
| 4.1 | Record trade decisions with entry price and timestamp for outcome tracking | track:calibration, parallel-safe | — |
| 4.2 | Add price lookback mechanism for T+N outcome evaluation | track:calibration, parallel-safe | — |
| 4.3 | Implement OutcomeTracker to evaluate decisions against actual prices | track:calibration, sequential | 4.1, 4.2 |
| 4.4 | Implement CalibrationEngine with anomaly-score bucketing | track:calibration, sequential | 4.3 |
| 4.5 | Add calibration drift detection and alert metrics | track:calibration, sequential | 4.4 |
| 4.6 | Persist outcome records to blob store | track:calibration, sequential | 4.3 |

### Workstream 5: Risk Observability and Suspicious Position Detection

| # | Issue Title | Labels | Blocked By |
|---|---|---|---|
| 5.1 | Instrument RiskEngine.evaluate with Prometheus metrics | track:risk-obs, parallel-safe | — |
| 5.2 | Add near-limit exposure detector to risk engine | track:risk-obs, parallel-safe | — |
| 5.3 | Add concentration risk detector for correlated near-limit symbols | track:risk-obs, sequential | 5.2 |
| 5.4 | Add one-directional accumulation detector | track:risk-obs, parallel-safe | — |
| 5.5 | Persist suspicious position alerts to blob store | track:risk-obs, sequential | 5.2, 5.3, 5.4 |
| 5.6 | Add Grafana "Risk Health" dashboard panel | track:risk-obs, sequential | 5.1, 5.5 |

### Workstream 6: E2E Integration Tests

| # | Issue Title | Labels | Blocked By |
|---|---|---|---|
| 6.1 | Create docker-compose.test.yaml overlay for e2e tests | track:e2e, parallel-safe | — |
| 6.2 | Build test helper to publish known events to Kafka order topic | track:e2e, parallel-safe | — |
| 6.3 | Write e2e test: Kafka to markettransformer to RabbitMQ signal exchange | track:e2e, sequential | 6.1, 6.2 |
| 6.4 | Write e2e test: signal exchange to markettrade blob output | track:e2e, sequential | 6.3 |
| 6.5 | Write e2e test: signal exchange to marketbard blob output | track:e2e, sequential | 6.3 |
| 6.6 | Write e2e test: Kafka to marketappendonly history.log | track:e2e, sequential | 6.1, 6.2 |
| 6.7 | Add make test-e2e target and GitHub Actions nightly workflow | track:e2e, sequential | 6.3, 6.4, 6.5, 6.6 |

---

## Recommended Execution Order

1. **Resilience** (PRD 1) and **Observability** (PRD 2) — run in parallel. These are foundational: without them, you cannot safely debug the later workstreams.
2. **Trade Validation** (PRD 3) — depends on resilience (DLQ for rejected messages).
3. **Trade Outcome Tracking** (PRD 4) and **Risk Observability** (PRD 5) — run in parallel. Both are analytical layers that depend on the pipeline being stable.
4. **E2E Tests** (PRD 6) — last, once all modules have their production behavior in place.
