.PHONY: run worker test

# Both targets expect Postgres to be running already.
# Server: DATABASE_URL from the environment / .env, or the app default (localhost:5432).
PORT ?= 8000
TEST_DATABASE_URL ?= postgresql+asyncpg://test:test@localhost:5436/test

run: ## Apply migrations and run the API with auto-reload
	uv run alembic upgrade head
	uv run uvicorn app.main:app --reload --port $(PORT)

worker: ## Run the summary worker (needs OPENAI_API_KEY)
	uv run python -m app.worker

test: ## Run tests; extra pytest args via ARGS, e.g. make test ARGS="-k search -x"
	DATABASE_URL=$(TEST_DATABASE_URL) uv run pytest $(ARGS)
