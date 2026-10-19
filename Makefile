.DEFAULT_GOAL := help
BACKEND := cd backend &&
FRONTEND := cd frontend &&

.PHONY: help up down logs seed install test test-unit test-bdd lint fmt migrate migration web-test e2e

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------- stack
up: ## Build and start the full stack (http://localhost:3000)
	docker compose up --build -d

down: ## Stop the stack
	docker compose down

logs: ## Follow api + worker logs
	docker compose logs -f api worker

seed: ## Seed demo data (idempotent)
	docker compose exec api python -m taskmanager.seed

# ---------------------------------------------------------------- local dev
install: ## Install backend + frontend dependencies and git hooks
	$(BACKEND) uv sync
	$(FRONTEND) npm ci
	uv run --project backend pre-commit install

test: ## Backend: all tests with coverage gate (needs Docker for Postgres)
	$(BACKEND) uv run pytest --cov --cov-report=term-missing

test-unit: ## Backend: fast unit tests only (no database)
	$(BACKEND) uv run pytest tests/unit

test-bdd: ## Backend: Gherkin acceptance scenarios
	$(BACKEND) uv run pytest tests/step_defs -m "not wip" -v

lint: ## All static checks: ruff, mypy, import-linter, eslint, tsc, prettier
	$(BACKEND) uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run lint-imports
	$(FRONTEND) npm run lint && npm run typecheck && npm run format:check

fmt: ## Auto-format everything
	$(BACKEND) uv run ruff check --fix . && uv run ruff format .
	$(FRONTEND) npm run format

migrate: ## Apply migrations to DATABASE_URL
	$(BACKEND) uv run alembic upgrade head

migration: ## Create a migration: make migration m="add x"
	$(BACKEND) uv run alembic revision --autogenerate -m "$(m)"

web-test: ## Frontend unit/component tests with coverage
	$(FRONTEND) npx vitest run --coverage

e2e: ## Playwright smoke test against the running stack
	$(FRONTEND) E2E_BASE_URL=http://localhost:3000 npm run e2e
