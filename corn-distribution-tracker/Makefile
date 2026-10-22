# Developer commands - see README.md for full environment setup.
SHELL := /bin/bash
PY ?= .venv/bin/python
PIP ?= .venv/bin/pip
ARGS ?=

.PHONY: help venv api-install web-install migrate migrate-down test-api test-web \
        lint-api lint-web typecheck-api typecheck-web build-web run-api run-web dev-up dev-dump-clean

venv:
	python3 -m venv .venv && $(PIP) install --upgrade pip

api-install: venv
	$(PIP) install -r apps/api/requirements.txt -r apps/api/requirements-dev.txt

web-install:
	cd apps/web && npm ci

migrate:
	cd apps/api && ../../.venv/bin/alembic upgrade head

migrate-down:
	cd apps/api && ../../.venv/bin/alembic downgrade -1

create-admin:
	cd apps/api && ../../.venv/bin/python -m app.cli.create_admin $(ARGS)

test-api:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest apps/api/tests

test-web:
	cd apps/web && npm test

lint-api:
	.venv/bin/ruff check apps/api/app apps/api/tests

lint-web:
	cd apps/web && npx eslint src --max-warnings=0

typecheck-api:
	.venv/bin/mypy apps/api/app --config-file apps/api/pyproject.toml

typecheck-web:
	cd apps/web && npx tsc -b --noEmit

build-web:
	cd apps/web && npm run build

dev-up: ## start docker compose stack
	docker compose up --build

run-api:
	cd apps/api && ../../.venv/bin/uvicorn app.main:app --reload --port 8000

run-web:
	cd apps/web && npm run dev
