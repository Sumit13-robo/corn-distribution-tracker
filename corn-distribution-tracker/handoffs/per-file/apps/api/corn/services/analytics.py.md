# File Handoff: `apps/api/corn/services/analytics.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Dashboard, distributor/site analytics, map data and CSV calculations

## Current implementation

Dashboard, distributor/site analytics, map data and CSV calculations. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 66 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 50 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (8 passed).

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.

## Campaign-site update (2026-10-25)

Map-site and site-analytics queries filter sites by the selected campaign, so a site belonging to another campaign cannot appear with a zero target. Map-site queries also omit sites without reference coordinates instead of inventing positions. Verification: `make test-api` → 66 passed (including a campaign-scope/name-only analytics test); Ruff/mypy clean.

## Integrity-only flag counts (2026-10-25)

Dashboard and site `flagged` counts now count only non-location evidence-integrity flags. Legacy location flags in stored records are ignored for metrics. Legacy map payloads still omit name-only sites rather than inventing coordinates. Verification: `make test-api` → 66 passed; Ruff/mypy clean.

## Delivery-point map (2026-10-25)

Added `map_deliveries()` for the admin delivery map. It queries `DistributionRecord` with non-null captured latitude/longitude and status `SUBMITTED` or `APPROVED`, excludes rejected/cancelled claims, supports `campaign_id`, `distributor_user_id` and bbox filters, and returns site/distributor display fields, quantity, status, submitted time and location metadata without evidence URLs. Site reference coordinates are never used. `map_sites()` remains as a legacy API view but is no longer consumed by the SPA.

Verification: `make test-api` → 67 passed; Ruff clean; mypy clean in 50 source files; no migration change.
