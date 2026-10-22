# File Handoff: `apps/web/e2e/support/config.ts`

**Status:** TESTED
**Primary owner:** QA
**File purpose:** Shared E2E identifiers and fixture bytes

## Responsibility
Define the fixed synthetic identities, site coordinates, campaign/site codes and evidence fixture; resolve the disposable database URL from `E2E_DATABASE_URL`.

## Contract and dependencies
Playwright config, global setup, setup and workflow specs.

## Implementation summary
Public test-only values (no passwords) with a default local PostgreSQL URL. Contains a small PNG generated with Pillow (valid signature and decodable by the server) used as synthetic evidence; it carries no personal data or geotags.

**Verification (2026-10-22):** consumed by the passing 7-test E2E run.

**Unresolved issues:** Defaults assume local PostgreSQL on port 5432; use `E2E_DATABASE_URL` otherwise.
