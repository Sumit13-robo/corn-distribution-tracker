# File Handoff: `apps/api/corn/views/health.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Unauthenticated liveness and readiness probes

## Current implementation

Unauthenticated liveness and readiness probes. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 98 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 51 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (9 passed).

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.

## 2026-10-26 audit remediation

Readiness now probes the configured storage service as well as the database; liveness stays dependency-free and neither endpoint leaks secrets.

Verification for the current tree: 98 API tests, 39 web tests, 9 Playwright E2E tests, Ruff/mypy/migration/build gates clean. External provider/container/proxy evidence remains operator-owned.
