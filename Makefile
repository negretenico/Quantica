.PHONY: up down build test build-listener build-transformer build-bard test-listener test-transformer test-bard

up:
	docker compose up -d --build

down:
	docker compose down -v

build: build-listener build-transformer build-bard

build-listener:
	cd marketListener && mvn clean package -DskipTests

build-transformer:
	cd markettransformer && mvn clean package -DskipTests

build-bard:
	cd marketbard && pip install -r requirements.txt

test: test-listener test-transformer test-bard

test-listener:
	cd marketListener && mvn test

test-transformer:
	cd markettransformer && mvn test

test-bard:
	cd marketbard && python -m pytest tests/ -v
