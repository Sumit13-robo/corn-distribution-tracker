# File Handoff: `apps/api/app/schemas/analytics.py`

**Status:** TESTED  
**Primary owner:** Backend  
**File purpose:** Analytics schemas

## Responsibility
Typed overview/performance response models with decimal-string quantities and integer counts.

## Contract and dependencies
See the relevant contract under `docs/` and the ownership table in `handoffs/file_map.md`; this file was added during implementation and integrates with the shared API/session/query layers.

## Implementation summary

Typed overview/performance response models with decimal-string quantities and integer counts.

**Verification (2026-10-22):** `make test-api` → 45 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 65 files; fresh PostgreSQL DB `alembic upgrade head → downgrade base → upgrade head` passed.

**Unresolved issues:** None known.
