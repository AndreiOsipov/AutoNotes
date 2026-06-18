.PHONY: install up up-prod down check-migrations migrate lint test

up:
	docker compose -f docker-compose.yml -f infra/docker-compose.dev.yml up --build

up-prod:
	docker compose -f docker-compose.yml up -d --build

down:
	docker compose down

check-migrations:
	uv run alembic check

migrate:
	uv run alembic upgrade head

lint:
	uvx ruff check .

test:
	uv run pytest
