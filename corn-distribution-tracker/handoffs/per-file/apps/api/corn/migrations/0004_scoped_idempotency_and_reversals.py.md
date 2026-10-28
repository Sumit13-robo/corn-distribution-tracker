# File Handoff: `apps/api/corn/migrations/0004_scoped_idempotency_and_reversals.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Scope legacy idempotency keys and add reversal/review schema safely.

## Current implementation

- Adds `idempotency_scope` and `idempotency_fingerprint` to stock movements, backfills legacy scopes from movement type/source and installs the scoped uniqueness constraint.
- Adds `reversal_of_id`, `reversed_by_id`, delivery review/exception fields and record status support.
- Temporarily drops the append-only stock-movement trigger **inside the migration transaction**, backfills rows, then recreates the trigger before commit. Audit-event triggers are untouched.

## Verification

- Applied cleanly to fresh test databases.
- A scratch database was migrated from `0001` through `0004` with the trigger temporarily removed/recreated; legacy scope backfill verified.
- The synthetic restore drill restored migrations `0001`–`0004` and confirmed the append-only trigger plus reversal/idempotency columns.
- `makemigrations --check --dry-run` reports no drift.

## Unresolved issues

Legacy rows have no stored request fingerprint. Application code fails them closed and requires a new key instead of guessing a replay; operators should re-key any offline client during the upgrade window.
