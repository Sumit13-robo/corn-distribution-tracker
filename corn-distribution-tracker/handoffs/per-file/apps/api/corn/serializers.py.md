# File Handoff: `apps/api/corn/serializers.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Strict DRF input serializers for every mutation boundary

## Current implementation

Strict DRF input serializers for every mutation boundary. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 98 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 51 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (9 passed).

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.

## Campaign-site update (2026-10-25)

`CampaignCreateSerializer` accepts an optional `sites` list (max 200, trimmed and case-insensitively de-duplicated). `SiteCreateSerializer` accepts optional `campaign_id`, `site_code`, and nullable coordinates; `SitePatchSerializer` allows both coordinates to be cleared. `AssignmentCreateSerializer` still accepts an optional campaign. Verification: `make test-api` → 98 passed, Ruff/mypy clean.
