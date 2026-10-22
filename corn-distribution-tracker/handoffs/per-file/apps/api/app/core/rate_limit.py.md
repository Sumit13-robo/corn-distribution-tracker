# File Handoff: `apps/api/app/core/rate_limit.py`

**Status:** TESTED  
**Primary owner:** Backend  
**File purpose:** Auth rate limiting

## Responsibility
Lightweight in-process limiter for login/refresh/reset attempts; no secrets logged and conservative defaults.

## Contract and dependencies
See the relevant contract under `docs/` and the ownership table in `handoffs/file_map.md`; this file was added during implementation and integrates with the shared API/session/query layers.

## Implementation summary

Lightweight in-process limiter for login/refresh/reset attempts; no secrets logged and conservative defaults.

**Verification (2026-10-22):** `make test-api` → 46 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 65 files; fresh PostgreSQL DB `alembic upgrade head → downgrade base → upgrade head` passed.

**Unresolved issues:** None known.
