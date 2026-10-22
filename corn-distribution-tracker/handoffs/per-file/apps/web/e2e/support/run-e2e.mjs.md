# File Handoff: `apps/web/e2e/support/run-e2e.mjs`

**Status:** TESTED
**Primary owner:** QA
**File purpose:** Prepare the disposable Django E2E database before Playwright starts web servers.

## Current implementation

Runs `prepare_db.py` and `manage.py migrate` with the E2E database URL, then executes the local Playwright CLI with the remaining arguments. This ordering matters because Playwright launches `webServer` processes before `globalSetup`; without the pre-step a fresh checkout would start Django against a missing database. The database name guard and all synthetic-data rules remain in `prepare_db.py`.

## Verification

`npm run test:e2e` → 8 passed (2 setup + 6 workflow) on a freshly recreated Django/PostgreSQL database. The wrapper also reproduced a clean first-run setup after the E2E database had been dropped.

## Unresolved issues

Requires the repo virtualenv or `E2E_PYTHON`, PostgreSQL with CREATEDB, and Chromium. Destructive to the dedicated `*e2e*` database only.
