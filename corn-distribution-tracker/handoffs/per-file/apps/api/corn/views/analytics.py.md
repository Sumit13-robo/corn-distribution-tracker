# File Handoff: `apps/api/corn/views/analytics.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Analytics endpoints and audited CSV export

## Current implementation

Analytics endpoints and audited CSV export. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 98 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 51 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (9 passed).

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.

## Delivery-map endpoint (2026-10-25)

Added admin-only `GET /api/v1/analytics/map-deliveries`, sharing the existing bbox parser and campaign/distributor UUID query helpers with the legacy map-sites endpoint. The response is rebuilt from `analytics_service.map_deliveries()` and exposes no evidence URLs. Invalid bbox input returns the existing `422`. Verification: `make test-api` → 98 passed; Ruff/mypy clean.
