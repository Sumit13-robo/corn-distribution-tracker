# File Handoff: `apps/api/corn/services/audit.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Append-only audit writer and request-context extraction

## Current implementation

Append-only audit writer and request-context extraction. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 98 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 51 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (9 passed).

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.

## 2026-10-26 audit remediation

Forwarded client IPs are accepted only when `TRUST_X_FORWARDED_FOR=true`; proxy headers are otherwise ignored. Referer handling has a safe fallback.

Verification for the current tree: 98 API tests, 39 web tests, 9 Playwright E2E tests, Ruff/mypy/migration/build gates clean. External provider/container/proxy evidence remains operator-owned.
