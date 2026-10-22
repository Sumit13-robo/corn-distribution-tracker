# File Handoff: `apps/web/e2e/global-setup.ts`

**Status:** TESTED
**Primary owner:** QA
**File purpose:** Per-run credentials and first-admin bootstrap for Playwright.

## Current implementation

Runs after Playwright starts its web servers and before the `setup` project. Generates random admin/distributor passwords in the gitignored `apps/web/e2e/.state/` directory, runs Django migrations against the already-created E2E database, and invokes `create_admin` via the password environment variable. Database recreation/migration before web-server startup is handled by `e2e/support/run-e2e.mjs`.

## Verification

`npm run test:e2e` → 8 passed from a clean E2E database. Credentials are synthetic and are not committed.

## Unresolved issues

None known.
