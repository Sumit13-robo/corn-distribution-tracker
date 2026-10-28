# File Handoff: `apps/web/e2e/support/prepare_db.py`

**Status:** TESTED
**Primary owner:** QA
**File purpose:** Recreate only the disposable E2E PostgreSQL database.

## Current implementation

Derives a maintenance connection from `E2E_DATABASE_URL`, validates the PostgreSQL scheme and a safe database name containing `e2e`, then drops/recreates that database with `WITH (FORCE)`. It runs from `run-e2e.mjs` before Playwright starts Django. The connecting role must own the E2E database or be able to create/drop it.

## Verification

Exercised on a fresh clean-database run; `npm run test:e2e` → 9 passed. The target is always the isolated `corn_tracker_e2e` database.

## Unresolved issues

If a database with the same name is owned by a different role, PostgreSQL refuses the drop with `must be owner of database`; drop it with the owning role first. No real database should be targeted.
