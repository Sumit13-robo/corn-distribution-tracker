# File Handoff: `apps/api/corn/views/sites.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Site management and progress endpoints

## Current implementation

Site management and progress endpoints. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 98 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 51 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (9 passed).

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.

## Campaign-site update (2026-10-25)

Site list supports admin `campaign_id` filtering; create/patch return nullable coordinates and `campaign_id`. `/sites` remains the API resource even though the standalone SPA page was removed. Verification: `make test-api` → 98 passed; Ruff/mypy clean.

## Integrity-only flagged counts (2026-10-25)

Site list/detail flag counts use non-location evidence-integrity flags only; location quality is not a warning. `/sites` create/patch still accepts legacy geofence/accuracy fields for compatibility but the UI does not expose them. Verification: `make test-api` → 98 passed; Ruff/mypy clean.
