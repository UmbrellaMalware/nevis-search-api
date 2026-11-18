.PHONY: run worker test migrate migration downgrade

# All targets expect Postgres to be running already.
# App and migrations: DATABASE_URL from the environment / .env, or the app default (localhost:5432).
PORT ?= 8000
TEST_DATABASE_URL ?= postgresql+asyncpg://test:test@localhost:5436/test

run: migrate ## Apply migrations and run the API with auto-reload
	uv run uvicorn app.main:app --reload --port $(PORT)

worker: ## Run the summary worker (needs OPENAI_API_KEY)
	uv run python -m app.worker

test: ## Run tests; extra pytest args via ARGS, e.g. make test ARGS="-k search -x"
	DATABASE_URL=$(TEST_DATABASE_URL) uv run pytest $(ARGS)

migrate: ## Apply all migrations
	uv run alembic upgrade head

# Next sequential revision id: 0005 -> 0006.
NEXT_REV = $(shell ls migrations/versions | grep -oE '^[0-9]+' | sort -n | tail -1 | awk '{printf "%04d", $$1 + 1}')

# Empty on purpose, no --autogenerate: indexes and constraints live only in migrations, not in
# app/models.py, so autogenerate would try to drop every one of them.
migration: ## New empty migration: make migration NAME="add client tags"
	@test -n "$(NAME)" || (echo 'usage: make migration NAME="short description"' && exit 1)
	uv run alembic revision --rev-id $(NEXT_REV) -m "$(NAME)"

downgrade: ## Roll back the last migration
	uv run alembic downgrade -1
