.PHONY: help up build down restart logs logs-api logs-db ps shell db migrate clean

DC = docker compose
API = messenger_api
DB = messenger_db

help:
	@echo "Messenger project commands:"
	@echo "  make up        - start app in background"
	@echo "  make build     - rebuild images and start app"
	@echo "  make down      - stop containers"
	@echo "  make restart   - restart app"
	@echo "  make logs      - show all logs"
	@echo "  make logs-api  - show API logs"
	@echo "  make logs-db   - show database logs"
	@echo "  make ps        - show containers"
	@echo "  make shell     - open shell in API container"
	@echo "  make db        - open psql in database container"
	@echo "  make migrate   - run application migrations"
	@echo "  make clean     - stop containers and remove volumes"

up:
	$(DC) up -d

build:
	$(DC) up -d --build

down:
	$(DC) down

restart:
	$(DC) restart

logs:
	$(DC) logs -f

logs-api:
	docker logs -f $(API)

logs-db:
	docker logs -f $(DB)

ps:
	$(DC) ps

shell:
	docker exec -it $(API) sh

db:
	docker exec -it $(DB) psql -U messenger -d messenger

migrate:
	docker exec -it $(API) python -m app.migrations

clean:
	$(DC) down -v
