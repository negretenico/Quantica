.PHONY: up down e2e-up e2e-down e2e-logs dev-ui run-server run-notify run-dlq build test build-listener build-transformer build-analysis build-bard build-risk build-trade build-notify build-dlq build-server build-ui build-e2e test-listener test-transformer test-analysis test-bard test-risk test-trade test-notify test-dlq test-server test-ui test-e2e test-backtest test-shared tunnel info logs health

up:
	docker compose up -d --build --remove-orphans

down:
	docker compose down -v --remove-orphans

e2e-up:
	docker compose -f docker-compose.yaml -f docker-compose.test.yaml up -d --build --remove-orphans

e2e-down:
	docker compose -f docker-compose.yaml -f docker-compose.test.yaml down -v --remove-orphans

e2e-logs:
	docker compose -f docker-compose.yaml -f docker-compose.test.yaml logs -f --tail=100

dev-ui:
	cd marketui && npm run dev

run-server:
	cd marketserver && py run.py

run-notify:
	cd marketnotify && py run.py

run-dlq:
	cd marketdlq && py run.py

build: build-listener build-transformer build-analysis build-bard build-risk build-trade build-notify build-dlq build-server build-ui

build-listener:
	cd marketListener && mvn clean package -DskipTests

build-transformer:
	cd markettransformer && mvn clean package -DskipTests

build-analysis:
	cd marketanalysis && py -m pip install -r requirements.txt

build-bard:
	cd marketbard && py -m pip install -r requirements.txt

build-risk:
	cd marketrisk && py -m pip install -e .

build-trade:
	cd markettrade && py -m pip install -e .

build-notify:
	cd marketnotify && py -m pip install -r requirements.txt

build-dlq:
	cd marketdlq && py -m pip install -r requirements.txt

build-server:
	cd marketserver && py -m pip install -r requirements.txt

build-ui:
	cd marketui && npm ci && npm run build

test: test-listener test-transformer test-analysis test-bard test-risk test-trade test-notify test-dlq test-server test-ui

test-listener:
	cd marketListener && mvn test

test-transformer:
	cd markettransformer && mvn test

test-analysis:
	cd marketanalysis && py -m pytest tests/ -v

test-bard:
	cd marketbard && py -m pytest tests/ -v

test-risk:
	cd marketrisk && py -m pytest tests/

test-trade:
	cd markettrade && py -m pytest tests/

test-notify:
	cd marketnotify && py -m pytest tests/ -v

test-dlq:
	cd marketdlq && py -m pytest tests/ -v

test-server:
	cd marketserver && py -m pytest tests/ -v

test-ui:
	cd marketui && npx vitest run

build-e2e:
	cd markete2e && py -m pip install -e .

test-e2e:
	cd markete2e && py -m pytest tests/ -v -m e2e

test-backtest:
	py -m pytest scripts/backtest/tests/ -v

test-shared:
	py -m pytest shared/tests/ -v

tunnel:
	cloudflared tunnel run QuanticaAPI

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
	@echo   Tunnel [API]          https://quantica-api.com
	@echo   marketnotify          [internal - Discord webhooks]
	@echo   marketdlq             [internal - DLQ monitor]
	@echo   marketui              http://localhost:3001
	@echo   Prometheus            http://localhost:9090
	@echo   Prometheus [Tunnel]   https://prometheus.quantica-api.com
	@echo   Grafana               http://localhost:3000
	@echo   Grafana [Tunnel]      https://grafana.quantica-api.com
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
