# File Handoff: `apps/api/app/main.py`

**Status:** TESTED  
**Primary owner:** Backend  
**File purpose:** API entrypoint

## Responsibility
Create the FastAPI app, lifespan hooks, CORS/security middleware, structured request IDs, exception handlers, `/health/live` and `/health/ready`, and mount v1 routers. Keep health output minimal and do not expose secrets.

## Contract and dependencies
Config, DB, router

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- Health and API smoke tests; app starts with validated config.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Builds the FastAPI app with request-id/security middleware, settings-driven CORS, the uniform JSON error envelope (validation, 404, AppError, unhandled), `/health/live` and `/health/ready` (DB + storage probes), and mounts all routers under `/api/v1`. Docs/OpenAPI are disabled in production.

**Verification (2026-10-22):** `make test-api` → 46 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 65 files; fresh PostgreSQL DB `alembic upgrade head → downgrade base → upgrade head` passed.

**Unresolved issues:** None known.
