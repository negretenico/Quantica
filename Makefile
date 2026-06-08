.PHONY: up down

up:
	docker compose up -d --build

down:
	docker compose down