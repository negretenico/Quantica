# Running Quantica

This project contains several modules that can run independently or together as a full market data pipeline.
Use this file as a quick-start reference for local development and full-stack execution.

## Full stack with Docker Compose

The root `docker-compose.yaml` defines Kafka, RabbitMQ, and the project modules.

1. Start the full stack:

```bash
make up
```

2. Stop the stack:

```bash
make down
```

If you do not have `make`, use:

```bash
docker compose up -d --build
```

and to stop:

```bash
docker compose down
```

## Module run order

The system is easiest to run in this order for local development:

1. `marketListener`
2. `markettransformer`
3. `marketanalysis`
4. `marketbard`
5. `marketappendonly`

## Local development commands

### marketListener

```bash
cd marketListener
./mvnw spring-boot:run -Dspring-boot.run.profiles=local
```

On Windows:

```powershell
cd marketListener
./mvnw.cmd spring-boot:run -Dspring-boot.run.profiles=local
```

### markettransformer

```bash
cd markettransformer
./mvnw spring-boot:run -Dspring-boot.run.profiles=local
```

On Windows:

```powershell
cd markettransformer
./mvnw.cmd spring-boot:run -Dspring-boot.run.profiles=local
```

### marketanalysis

```bash
cd marketanalysis
python -m pip install -r requirements.txt
python run.py
```

### marketbard

```bash
cd marketbard
pip install -r requirements.txt
python run.py
```

### marketappendonly

```bash
cd marketappendonly
go run cmd/server/main.go
```

## Environment notes

- The compose stack uses `KAFKA_BOOTSTRAP=quantica-kafka:29092` and `RABBITMQ_URL=amqp://guest:guest@quantica-rabbitmq/`.
- `marketbard` requires a local `.env` file with at least `OPENAI_API_KEY` and `GITHUB_TOKEN`.
- If you use root compose, make sure `GITHUB_TOKEN` is available in the shell environment.

## Troubleshooting tips

- Start Kafka and RabbitMQ first if running modules manually.
- Check each module's README for module-specific requirements and command examples.
- If a service fails to connect, verify the bootstrap server and RabbitMQ URL.
