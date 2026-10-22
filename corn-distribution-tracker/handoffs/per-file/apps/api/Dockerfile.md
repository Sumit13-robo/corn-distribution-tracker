# File Handoff: `apps/api/Dockerfile`

**Status:** IMPLEMENTED  
**Primary owner:** Backend  
**File purpose:** API container

## Responsibility
Build minimal non-root API image, install locked dependencies, expose app port, handle signals and avoid copying local secrets/test artifacts.

## Contract and dependencies
pyproject; main

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- Container boots and healthcheck succeeds.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Python 3.14-slim runtime image: unprivileged user, pinned requirements, read-only app code with a writable `/app/storage-data`, liveness healthcheck and uvicorn on :8000. Not built here (Docker unavailable).

**Verification (2026-10-22):** `make test-api` → 45 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 65 files; fresh PostgreSQL DB `alembic upgrade head → downgrade base → upgrade head` passed.

**Unresolved issues:** Image/compose build was not executed because Docker is unavailable in this environment.
