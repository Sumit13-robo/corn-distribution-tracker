# File Handoff: `apps/web/playwright.config.ts`

**Status:** TESTED
**Primary owner:** QA / Frontend
**File purpose:** Browser E2E orchestration

## Responsibility
Start the real API and Vite dev server for Playwright, wire the disposable database and private local evidence directory, configure geolocation, and run the setup project before the serial Chromium workflow.

## Contract and dependencies
`e2e/support/config.ts`; API `/health/live`; fixed local ports 8000/5173; repo `.venv` and `apps/api`; Chromium installed via `npx playwright install chromium`.

## Implementation summary
Two `webServer` entries start uvicorn (`APP_ENV=test`, E2E database, random per-run JWT secret, local evidence storage) and Vite (`VITE_API_BASE_URL=/api/v1`). Global setup recreates/migrates the database and bootstraps the admin; the `setup` project seeds the tenant world through public HTTP APIs; the `chromium` project runs six serial workflow tests with one worker, including a 360 px mobile viewport check. Geolocation is granted at the site's synthetic coordinates with 10 m accuracy. Traces/screenshots are retained on failure.

**Verification (2026-10-22):** `npm run test:e2e` → **8 passed** (2 setup + 6 workflow) against real PostgreSQL 17 and FastAPI; no browser mocks.

**Unresolved issues:** Requires local PostgreSQL with CREATEDB, repo venv and Chromium; ports must be free. No hosted CI pipeline is included.
