# File Handoff: `apps/web/playwright.config.ts`

**Status:** TESTED
**Primary owner:** QA/Frontend
**File purpose:** Browser E2E orchestration.

## Current implementation

Two `webServer` entries start Django (`runserver`, test settings, E2E database, local private storage) and Vite. Database recreation and migration happen in `e2e/support/run-e2e.mjs` before those servers start. Global setup creates per-run credentials and the first admin; the `setup` project seeds campaign/site/distributor/assignment/stock through public HTTP APIs; the `chromium` project runs six serial workflow tests with one worker, including a 360 px viewport check. Geolocation is granted at the synthetic site coordinates with 10 m accuracy. Traces/screenshots are retained on failure.

## Verification

`npm run test:e2e` → **9 passed** (2 setup + 6 workflow) against PostgreSQL 17, Django/DRF and the real SPA. No browser mocks.

## Unresolved issues

Local-only; requires PostgreSQL CREATEDB privileges and Chromium. Ports 8000 and 5173 must be free.
