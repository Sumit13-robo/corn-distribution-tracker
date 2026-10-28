# File Handoff: `apps/api/corn/errors.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Application exceptions, uniform JSON error envelope and DRF/Django error handling

## Current implementation

Application exceptions, uniform JSON error envelope and DRF/Django error handling. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 98 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 51 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (9 passed).

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.
