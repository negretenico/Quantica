.PHONY: up down build test build-listener build-transformer build-risk test-listener test-transformer test-risk

up:
	docker compose up -d --build

down:
	docker compose down -v

build: build-listener build-transformer build-risk

build-listener:
	cd marketListener && mvn clean package -DskipTests

build-transformer:
	cd markettransformer && mvn clean package -DskipTests

build-risk:
	cd marketrisk && pip install -e .

test: test-listener test-transformer test-risk

test-listener:
	cd marketListener && mvn test

test-transformer:
	cd markettransformer && mvn test

test-risk:
	cd marketrisk && pytest tests/
