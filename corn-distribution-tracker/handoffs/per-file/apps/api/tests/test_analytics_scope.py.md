# File Handoff: `apps/api/tests/test_analytics_scope.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Analytics scope, denominators and export authorization tests

## Current implementation

Analytics scope, denominators and export authorization tests. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 66 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 50 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (8 passed).

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.

## Delivery-map coverage (2026-10-25)

Added a test proving `/analytics/map-deliveries` returns only delivery records with a captured fix (a no-location submission is excluded), exposes the expected site/distributor/quantity/coordinate fields, rejects distributor access, honors bbox filtering/invalid-bbox validation, retains the point with status `APPROVED` after review, and excludes a rejected claim. Verification: `make test-api` → 67 passed.
