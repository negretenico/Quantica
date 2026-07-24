# Quantica

This README captures the design decisions, tradeoffs, and deployment lessons I encountered while building Quantica. It is written as a reflection on the architecture, tool choices, and operational challenges rather than as a strict user guide.

## Table of contents

- How it works
- Why so many modules
- Makefile build system
- Docker and Docker Compose
- RabbitMQ vs Kafka
- Why a ledger?
- Avoiding context bloat
- What was needed to deploy

### Docs

- [Running the application](docs/RUNNING.md)
- [Signal detectors](docs/DETECTORS.md)
- [Performance baselines](docs/PERFORMANCE.md)
- [Research](docs/research-binance-multi-symbol-websocket.md)

## Architecture diagram

A system-level architecture diagram is available at [`ARCHITECTURE.drawio`](ARCHITECTURE.drawio). Open it with [draw.io](https://app.diagrams.net) (desktop or web).

## How it works

Quantica listens to a single symbol (BTC) on the Binance websocket stream. Each incoming trade is published to a Kafka topic so we can normalize the message and perform anomaly detection. When a trade is read from the topic, we publish it as individual Spring events to decouple transformation from detection and make it easy to add new signal handlers.

When an anomaly is detected, the transformed event is pushed onto a message queue for workers to consume. We currently have two separate workers: one for ML inference on individual detections, and another for ML inference across aggregated events to provide an overview of the trading day.

## Why so many modules

I chose to split the system into multiple modules to reduce the cognitive load of a large monolithic application. This architecture lets each module focus on a single responsibility and avoids unnecessary dependencies between modules, such as Kafka clients or GitHub integration.

It also makes it easier to run each module in its own terminal instance and to use different AI agents for different parts of the system without them stepping on each other.

## Docker and Docker Compose

Each module has its own `Dockerfile` so it can be built and run independently. That keeps module environments isolated and reduces coupling between services.

Docker Compose is then used to describe the external services and internal relationships needed to run Quantica as a whole.

## Makefile build system

The polyglot nature of this application made a single build system impractical. I did not want to force every submodule to use the same build tool, because Java, Python, and other languages each solve different problems better.

Using `docker-compose` to orchestrate builds and `Makefile` targets to define common operations felt natural. With this approach, `make up` becomes a simple way to start the full application, assuming Docker Desktop is running on Windows.

## RabbitMQ vs Kafka

The original design used Kafka for service decoupling. Kafka is great for high throughput, but it also introduces operational overhead: brokers, consumer groups, partitioning, and more.

For our use case, we were effectively using Kafka as a job queue. RabbitMQ fits that pattern better, especially for the handoff to the analysis and bard workers where durability is less important and fire-and-forget delivery is acceptable.

## Why a ledger?

I originally added a market append-only log file to track transformed events. That turned out to be unnecessary because Kafka already provides an append-only log and replay capability. The file-based ledger was an initial design mistake caused by not fully recognizing Kafka’s built-in log semantics.

## Avoiding context bloat

To avoid context bloat, we split aggregation into time slices and analyzed each slice separately before summarizing the results. That is much more scalable than analyzing all 50K events at once.

This follows common data analysis patterns: break work into smaller chunks, process them independently, then combine the summaries.

## What was needed to deploy

AWS was a natural deployment choice because of its extensibility, broad adoption, and flexible pricing.

Key deployment tasks included:

- Creating secrets in AWS Secrets Manager for API keys and environment variables.
- Deciding between Amazon MQ and Amazon MSK for messaging infrastructure.
- Choosing a cheaper alternative: running RabbitMQ and Kafka containers on an EC2 instance instead of managed services.
- SSHing into the EC2 instance and installing Docker, RabbitMQ, and Kafka manually.
- Creating custom security groups in the VPC so instances could connect correctly to topics and queues.
- Iterating on CIDR blocks and task permissions until networking worked reliably.
- Creating IAM roles to allow access to secrets.
- Adding ECS task definitions for each service, including `markettransformer`, `marketanalysis`, and others.

After the instances were created in the AWS console, I updated them through the GitHub Actions CI/CD pipeline. Deploying to ECS introduced its own challenges, such as ensuring task definitions referenced secrets correctly and that `application-prod` properties were configured properly.
