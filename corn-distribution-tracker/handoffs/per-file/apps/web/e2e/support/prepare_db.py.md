# File Handoff: `apps/web/e2e/support/prepare_db.py`

**Status:** TESTED
**Primary owner:** QA
**File purpose:** Disposable E2E database creation

## Responsibility
Drop and recreate only the E2E database before Alembic runs, using a maintenance connection derived from `E2E_DATABASE_URL`.

## Contract and dependencies
SQLAlchemy/psycopg in the repo venv; PostgreSQL role with CREATEDB; explicit destructive E2E database.

## Implementation summary
Parses `E2E_DATABASE_URL`, validates the database name against `[A-Za-z0-9_]+` and requires the name to contain `e2e` (a guard against accidentally dropping a real database), connects to the `postgres` maintenance database in autocommit mode, then runs `DROP DATABASE IF EXISTS ... WITH (FORCE)` and `CREATE DATABASE`. Fails closed on unsafe names. Used only by Playwright global setup, never by application startup.

**Verification (2026-10-22):** recreated `corn_tracker_e2e` on each of the passing E2E runs; migrations and seeding followed.

**Unresolved issues:** Requires database-creation privileges. The default local URL is documented; CI/other hosts must set `E2E_DATABASE_URL`.
