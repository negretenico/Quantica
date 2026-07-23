.PHONY: up down build test build-listener build-transformer test-listener test-transformer

up:
	docker compose up -d --build

down:
	docker compose down -v

build: build-listener build-transformer

build-listener:
	cd marketListener && mvn clean package -DskipTests

build-transformer:
	cd markettransformer && mvn clean package -DskipTests

test: test-listener test-transformer

test-listener:
	cd marketListener && mvn test

test-transformer:
	cd markettransformer && mvn test
