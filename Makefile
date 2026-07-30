.PHONY: up down build test build-listener build-transformer build-bard build-risk build-trade build-server test-listener test-transformer test-bard test-risk test-trade test-server test-backtest test-shared

up:
	docker compose up -d --build --remove-orphans

down:
	docker compose down -v --remove-orphans

build: build-listener build-transformer build-bard build-risk build-trade build-server

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

test: test-listener test-transformer test-bard test-risk test-trade test-server

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

test-backtest:
	py -m pytest scripts/backtest/tests/ -v

test-shared:
	py -m pytest shared/tests/ -v
