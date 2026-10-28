# File Handoff: `apps/api/config/urls.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Root URL map for health, API v1 and JSON error handlers

## Current implementation

Root URL map for health, API v1 and JSON error handlers. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 98 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 51 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (9 passed).

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.

## Delivery-map route (2026-10-25)

Added `GET /api/v1/analytics/map-deliveries` before the legacy map-sites route. Verification: `make test-api` → 98 passed; Ruff/mypy clean.

## 2026-10-26 audit remediation

Kept readiness/liveness and evidence completion routes wired through the canonical URL map.

Verification for the current tree: 98 API tests, 39 web tests, 9 Playwright E2E tests, Ruff/mypy/migration/build gates clean. External provider/container/proxy evidence remains operator-owned.
