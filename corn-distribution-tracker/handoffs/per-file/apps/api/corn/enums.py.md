# File Handoff: `apps/api/corn/enums.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Canonical TextChoices values shared by models, services and serializers

## Current implementation

Canonical TextChoices values shared by models, services and serializers. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 98 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 51 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (9 passed).

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.

## 2026-10-26 audit remediation

Added the `REVERSED` distribution-record state and review/exception values used by compensating ledger reversals.

Verification for the current tree: 98 API tests, 39 web tests, 9 Playwright E2E tests, Ruff/mypy/migration/build gates clean. External provider/container/proxy evidence remains operator-owned.
