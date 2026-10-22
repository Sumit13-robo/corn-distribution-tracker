# File Handoff: `apps/api/app/models/__init__.py`

**Status:** IMPLEMENTED  
**Primary owner:** Backend  
**File purpose:** Package marker importing all models for metadata discovery

## Responsibility
Package marker importing all models for metadata discovery.

## Contract and dependencies
See the relevant contract under `docs/` and the ownership table in `handoffs/file_map.md`; this file was added during implementation and integrates with the shared API/session/query layers.

## Implementation summary

Package marker importing all models for metadata discovery.

**Verification (2026-10-22):** `make test-api` → 46 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 65 files; fresh PostgreSQL DB `alembic upgrade head → downgrade base → upgrade head` passed.

**Unresolved issues:** None known.
