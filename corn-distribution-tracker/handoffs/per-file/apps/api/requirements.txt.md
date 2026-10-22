# File Handoff: `apps/api/requirements.txt`

**Status:** TESTED  
**Primary owner:** Backend  
**File purpose:** Runtime dependency pins

## Responsibility
Exact runtime pins matching the validated virtualenv, including `email-validator` (required by pydantic `EmailStr` at import time). A fresh runtime-only install was verified to import the app without any dev packages.

## Contract and dependencies
See the relevant contract under `docs/` and the ownership table in `handoffs/file_map.md`; this file was added during implementation and integrates with the shared API/session/query layers.

## Implementation summary

Exact runtime pins matching the validated virtualenv, including `email-validator` (required by pydantic `EmailStr` at import time). A fresh runtime-only install was verified to import the app without any dev packages.

**Verification (2026-10-22):** `make test-api` → 45 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 65 files; fresh PostgreSQL DB `alembic upgrade head → downgrade base → upgrade head` passed.

**Unresolved issues:** None known.
