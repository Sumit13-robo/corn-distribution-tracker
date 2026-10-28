# File Handoff: `apps/api/corn/views/deliveries.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Distributor submission and admin review endpoints

## Current implementation

Distributor submission and admin review endpoints. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 98 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 51 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (9 passed).

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.

## 2026-10-26 audit remediation

Delivery views expose reversal detail, enforce approval idempotency headers and validate admin-only review transitions.

Verification for the current tree: 98 API tests, 39 web tests, 9 Playwright E2E tests, Ruff/mypy/migration/build gates clean. External provider/container/proxy evidence remains operator-owned.
