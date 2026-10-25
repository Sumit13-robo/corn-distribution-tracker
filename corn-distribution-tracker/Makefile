# Developer commands - see README.md for full environment setup.
SHELL := /bin/bash
PY ?= .venv/bin/python
PIP ?= .venv/bin/pip
ARGS ?=

.PHONY: help venv api-install web-install e2e-install migrate migrate-check create-admin test-api test-web \
        test-e2e lint-api lint-web typecheck-api typecheck-web build-web run-api run-web health

help:
	@grep -E '^[a-zA-Z_-]+:' Makefile | sort

venv:
	python3 -m venv .venv && $(PIP) install --upgrade pip

api-install: venv
	$(PIP) install -r apps/api/requirements.txt -r apps/api/requirements-dev.txt

web-install:
	cd apps/web && npm ci

e2e-install:
	cd apps/web && npx playwright install chromium

migrate:
	cd apps/api && ../../.venv/bin/python manage.py migrate

migrate-check:
	cd apps/api && ../../.venv/bin/python manage.py makemigrations --check --dry-run

create-admin:
	cd apps/api && ../../.venv/bin/python manage.py create_admin $(ARGS)

test-api:
	cd apps/api && DJANGO_SETTINGS_MODULE=config.settings_test PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
		../../.venv/bin/pytest -p pytest_django.plugin tests -q

test-web:
	cd apps/web && npm test

test-e2e:
	cd apps/web && npm run test:e2e

lint-api:
	.venv/bin/ruff check apps/api/config apps/api/corn apps/api/tests apps/api/manage.py

lint-web:
	cd apps/web && npx eslint src --max-warnings=0

typecheck-api:
	cd apps/api && ../../.venv/bin/mypy config corn --config-file pyproject.toml

typecheck-web:
	cd apps/web && npx tsc -b --noEmit

build-web:
	cd apps/web && npm run build

run-api:
	cd apps/api && ../../.venv/bin/python manage.py runserver 127.0.0.1:8000

run-web:
	cd apps/web && npm run dev

health:
	curl -fsS http://127.0.0.1:8000/health/live
	@echo
	curl -fsS http://127.0.0.1:8000/health/ready
	@echo
