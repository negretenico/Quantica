.PHONY: up down build test build-listener build-transformer build-bard build-risk build-trade test-listener test-transformer test-bard test-risk test-trade

up:
	docker compose up -d --build

down:
	docker compose down -v

build: build-listener build-transformer build-bard build-risk build-trade

build-listener:
	cd marketListener && mvn clean package -DskipTests

build-transformer:
	cd markettransformer && mvn clean package -DskipTests

build-bard:
	cd marketbard && pip install -r requirements.txt

build-risk:
	cd marketrisk && pip install -e .

build-trade:
	cd markettrade && pip install -e .

test: test-listener test-transformer test-bard test-risk test-trade

test-listener:
	cd marketListener && mvn test

test-transformer:
	cd markettransformer && mvn test

test-bard:
	cd marketbard && python -m pytest tests/ -v

test-risk:
	cd marketrisk && pytest tests/

test-trade:
	cd markettrade && pytest tests/
