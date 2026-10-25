# File Handoff: `apps/api/tests/conftest.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Backend fixtures for temporary databases, session/CSRF clients, tenant world and synthetic uploads

## Current implementation

Backend fixtures for temporary databases, session/CSRF clients, tenant world and synthetic uploads. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 66 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 50 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (8 passed).

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.
