# File Handoff: `apps/api/tests/test_inventory_ledger.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Ledger postings, reservations, reversals, append-only triggers and concurrency tests

## Current implementation

Ledger postings, reservations, reversals, append-only triggers and concurrency tests. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 98 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 51 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (9 passed).

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.
