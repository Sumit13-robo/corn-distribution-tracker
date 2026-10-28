# File Handoff: `apps/api/tests/test_distribution_submission.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Submission, review transitions, idempotency and evidence validation tests

## Current implementation

Submission, review transitions, idempotency and evidence validation tests. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 98 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 51 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (9 passed).

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.

## Location-independent approval coverage (2026-10-25)

Tests now assert that a submission with no fix, a stale fix, an inaccurate fix or a far-away fix is approved manually without an exception and posts one movement. Evidence-integrity override tests remain for duplicate hash/capture-time mismatch/unexpected type, and target overruns still require a reason. Verification: `make test-api` → 98 passed.
