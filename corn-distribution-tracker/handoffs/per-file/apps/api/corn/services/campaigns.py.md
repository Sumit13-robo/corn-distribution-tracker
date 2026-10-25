# File Handoff: `apps/api/corn/services/campaigns.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Campaigns, sites and distributor assignment domain rules

## Current implementation

Campaigns, sites and distributor assignment domain rules. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 66 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 50 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (8 passed).

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.

## Campaign-site update (2026-10-25)

Campaign creation creates the campaign and its optional name-only sites transactionally. Site creation validates one-campaign ownership, case-insensitive name uniqueness within a campaign, optional coordinate pairs and generated unique `site_code` values. Updates allow adding, changing or clearing a location with audit records. Assignment creation rejects a campaign-scoped site from a different campaign and adopts legacy/global sites on first assignment. Verification: `make test-api` → 66 passed (including 4 new campaign-site tests), Ruff/mypy clean.
