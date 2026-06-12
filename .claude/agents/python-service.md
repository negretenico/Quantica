---
name: python-service
description: Use for all work inside marketanalysis or marketbard — Python 3.11, kafka-python-ng, Flask (analysis only), Redis, OpenAI, GitHub API, threading.
---

You are working inside a Python 3.11 service of the Quantica project.

## Modules in scope
- `marketanalysis` — Flask service that consumes enriched `SignalEvent`s from Kafka, applies MiniBatchKMeans clustering, detects anomalies, and publishes results back to Kafka.
- `marketbard` — Worker process (no HTTP server) that consumes Kafka events, buffers them in Redis, generates Markdown stories via OpenAI, and commits them to GitHub.

## Package structure (both modules follow this)
```
app/         — config, Flask app or main wiring
model/       — ML model or LLM client + prompt builder
apache_kafka/ or app/ — Kafka consumer/producer
redis_cache/ — Redis client (marketbard only)
gh/          — GitHub client (marketbard only)
run.py       — entry point
```

## Key patterns
- All env vars read through `app/config.py` `Config` class — never `os.getenv` inline.
- Concurrent workers via `threading.Thread(target=..., daemon=True)`.
- Kafka consumer uses `register_handler(topic, callable)` pattern; topics subscribed at registration time.
- `kafka-python-ng` — not the original `kafka-python`.
- marketbard pipeline: Kafka → `redis_client.add_to_buffer()` → `flush_buffer_if_ready()` → `get_latest_gen_queue()` → OpenAI → `add_story()` → `get_latest_story()` → GitHub.
- marketanalysis: `model/mini_batch.py` holds the `MiniBatchKMeans` wrapper; `analysis/outbound.py` handles anomaly event publishing.

## What NOT to do
- Do not scatter `os.getenv` outside of `config.py`.
- Do not block the main thread — use daemon threads for workers.
- Do not use synchronous Kafka poll loops in the main thread.
- Do not add Flask to marketbard — it is a pure worker process.
