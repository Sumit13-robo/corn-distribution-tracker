# File Handoff: `apps/api/corn/models.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Django ORM schema, constraints, indexes and append-only table mappings

## Current implementation

Django ORM schema, constraints, indexes and append-only table mappings. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 98 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 51 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (9 passed).

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.

## Campaign-site update (2026-10-25)

`DistributionSite` now has a nullable `campaign` FK (`related_name="sites"`) and nullable `latitude`/`longitude`; a site can belong to at most one campaign. Name-only sites have null reference coordinates and no distance; location quality never gates approval. `distributionsite` migration state is `0003_campaign_sites_optional_location` (applied in development). Verification: `make test-api` → 98 passed, `make lint-api` → clean, `make typecheck-api` → 50 files clean, migration check → no changes.

## 2026-10-26 audit remediation

Added scoped idempotency columns/constraints, reversal links, delivery review/exception fields and `REVERSED` support while preserving append-only ledger/audit tables.

Verification for the current tree: 98 API tests, 39 web tests, 9 Playwright E2E tests, Ruff/mypy/migration/build gates clean. External provider/container/proxy evidence remains operator-owned.
