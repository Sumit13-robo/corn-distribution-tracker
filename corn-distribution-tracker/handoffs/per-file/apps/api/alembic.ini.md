# File Handoff: `apps/api/alembic.ini`

**Status:** TESTED  
**Primary owner:** Backend  
**File purpose:** Alembic configuration

## Responsibility
Configure script location, logging and migration entrypoint without hardcoding production connection secrets. Use environment-based connection setup in env.py.

## Contract and dependencies
alembic/env.py

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- Migration commands work without a committed DATABASE_URL.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Alembic config with `script_location = alembic` and runtime `DATABASE_URL`; exercised by the fresh-DB upgrade/downgrade/upgrade check.

**Verification (2026-10-22):** `make test-api` → 46 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 65 files; fresh PostgreSQL DB `alembic upgrade head → downgrade base → upgrade head` passed.

**Unresolved issues:** None known.
