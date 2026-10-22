# File Handoff: `apps/api/alembic/script.py.mako`

**Status:** IMPLEMENTED  
**Primary owner:** Backend  
**File purpose:** Standard Alembic revision template (boilerplate)

## Responsibility
Standard Alembic revision template (boilerplate).

## Contract and dependencies
See the relevant contract under `docs/` and the ownership table in `handoffs/file_map.md`; this file was added during implementation and integrates with the shared API/session/query layers.

## Implementation summary

Standard Alembic revision template (boilerplate).

**Verification (2026-10-22):** `make test-api` → 46 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 65 files; fresh PostgreSQL DB `alembic upgrade head → downgrade base → upgrade head` passed.

**Unresolved issues:** None known.
