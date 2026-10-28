# File Handoff: `.github/workflows/ci.yml`

**Status:** IMPLEMENTED
**Primary owner:** DevOps/Lead
**File purpose:** Continuous integration for backend, frontend, browser E2E and dependency review.

## Current implementation

Four jobs run on pushes and pull requests:

- **backend** — PostgreSQL 17 service, Python 3.13, Ruff, mypy, migration drift check, Django checks and the full API test suite.
- **frontend** — Node 22, `npm ci`, `npm audit --audit-level=high`, ESLint, TypeScript, Vitest and the production build.
- **e2e** — PostgreSQL 17 service, Python/Node install, Playwright Chromium with system dependencies and the real Django/Vite E2E flow against the disposable `corn_tracker_e2e` database.
- **dependency-review** — pull-request-only GitHub dependency review.

Permissions are limited to `contents: read`, jobs have timeouts and concurrency cancels superseded runs.

## Verification

The YAML parses locally; job names, PostgreSQL service image, E2E Playwright install step and required jobs were asserted. `npm audit` currently reports 0 vulnerabilities. The workflow has **not run on GitHub** because this change is uncommitted.

## Unresolved issues

Actions are referenced by major version tags rather than commit SHAs. The first hosted run must be observed before claiming CI-green status.
