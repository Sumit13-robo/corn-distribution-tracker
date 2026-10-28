# File Handoff: `apps/api/corn/services/inventory.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Double-entry ledger, postings, reservations, reversals and derived balances

## Current implementation

Double-entry ledger, postings, reservations, reversals and derived balances. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 98 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 51 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (9 passed).

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.

## 2026-10-26 audit remediation

Idempotency is scoped by operation and fingerprinted; legacy keys fail closed. Reversals are compensating only, cannot nest or overdraw, and mark deliveries `REVERSED`. `LOSS`/`RETURN` debit available stock so pending reservations cannot be consumed. Reconciliation uses two aggregate queries and checks net external flows against balances. First-site account creation tolerates races.

Verification for the current tree: 98 API tests, 39 web tests, 9 Playwright E2E tests, Ruff/mypy/migration/build gates clean. External provider/container/proxy evidence remains operator-owned.
