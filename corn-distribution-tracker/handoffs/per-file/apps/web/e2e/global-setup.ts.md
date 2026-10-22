# File Handoff: `apps/web/e2e/global-setup.ts`

**Status:** TESTED
**Primary owner:** QA
**File purpose:** E2E database/bootstrap lifecycle

## Responsibility
Create per-run synthetic credentials, recreate the disposable E2E database, apply Alembic migrations, and bootstrap the first administrator. Never touch non-E2E data.

## Contract and dependencies
`E2E_DATABASE_URL` (destructive), `E2E_PYTHON`, `E2E_LOCAL_STORAGE_DIR`; `e2e/support/prepare_db.py`; API Alembic config; first-admin CLI.

## Implementation summary
Playwright starts the web servers before global setup, but the API opens no database connection at import time, so it is safe to drop/recreate the database here. Passwords are generated with `crypto.randomBytes` and written mode `0600` to the gitignored `e2e/.state/credentials.json`; the admin is created via `app.cli.create_admin` using an environment-provided password. The evidence storage directory is created if absent (not recursively deleted, so an override cannot wipe an arbitrary path). The setup project runs only after this completes.

**Verification (2026-10-22):** exercised by `npm run test:e2e`; fresh database created, migrated and seeded on every run (7 passed).

**Unresolved issues:** Destructive by design; the README explicitly warns never to point `E2E_DATABASE_URL` at real data.
