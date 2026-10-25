# File Handoff: `apps/api/corn/presenters.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Canonical JSON response shaping, including site/distributor display fields

## Current implementation

Canonical JSON response shaping, including site/distributor display fields. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 66 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 50 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (8 passed).

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.

## Campaign-site update (2026-10-25)

`site_out` includes `campaign_id` and serializes nullable latitude/longitude as `null`. `distribution_out` already serializes nullable `distance_to_site_m`. Verification: `make test-api` → 66 passed; Ruff/mypy clean.
