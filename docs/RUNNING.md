# Running Quantica

## Start the full stack

```bash
make up
```

This starts Kafka, RabbitMQ, and all modules via Docker Compose. To stop:

```bash
make down
```

## Monitoring

Once the stack is running, open Grafana to observe pipeline metrics — throughput, Kafka consumer lag, and per-detector latency percentiles. Performance baselines are documented in [PERFORMANCE.md](PERFORMANCE.md).

## Environment requirements

- `marketbard` requires a `.env` file with `OPENAI_API_KEY` and `GITHUB_TOKEN`
- `GITHUB_TOKEN` must be available in the shell environment for the root compose to resolve GitHub Packages dependencies
