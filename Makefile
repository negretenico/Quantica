.PHONY: up down dev-ui run-server build test build-listener build-transformer build-bard build-risk build-trade build-server build-ui test-listener test-transformer test-bard test-risk test-trade test-server test-ui test-backtest test-shared info logs health

up:
	docker compose up -d --build --remove-orphans

down:
	docker compose down -v --remove-orphans

dev-ui:
	cd marketui && npm run dev

run-server:
	cd marketserver && py run.py

build: build-listener build-transformer build-bard build-risk build-trade build-server build-ui

build-listener:
	cd marketListener && mvn clean package -DskipTests

build-transformer:
	cd markettransformer && mvn clean package -DskipTests

build-bard:
	cd marketbard && py -m pip install -r requirements.txt

build-risk:
	cd marketrisk && py -m pip install -e .

build-trade:
	cd markettrade && py -m pip install -e .

build-server:
	cd marketserver && py -m pip install -r requirements.txt

build-ui:
	cd marketui && npm ci && npm run build

test: test-listener test-transformer test-bard test-risk test-trade test-server test-ui

test-listener:
	cd marketListener && mvn test

test-transformer:
	cd markettransformer && mvn test

test-bard:
	cd marketbard && py -m pytest tests/ -v

test-risk:
	cd marketrisk && py -m pytest tests/

test-trade:
	cd markettrade && py -m pytest tests/

test-server:
	cd marketserver && py -m pytest tests/ -v

test-ui:
	cd marketui && npm test

test-backtest:
	py -m pytest scripts/backtest/tests/ -v

test-shared:
	py -m pytest shared/tests/ -v

info:
	@echo .
	@echo === Quantica Services ===
	@echo .
	@echo   Kafka Broker 1        http://localhost:9092
	@echo   Kafka Broker 2        http://localhost:9094
	@echo   RabbitMQ AMQP         amqp://localhost:5672
	@echo   RabbitMQ Management   http://localhost:15672
	@echo   marketListener        http://localhost:8080
	@echo   marketanalysis        http://localhost:5000
	@echo   marketserver [API]    http://localhost:5001
	@echo   marketui              http://localhost:3001
	@echo   Prometheus            http://localhost:9090
	@echo   Grafana               http://localhost:3000
	@echo .
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
	@echo .

logs:
	docker compose logs -f --tail=100

health:
	@echo .
	@echo === Quantica Health Check ===
	@echo .
	@docker compose ps --format "table {{.Name}}\t{{.Status}}"
	@echo .
