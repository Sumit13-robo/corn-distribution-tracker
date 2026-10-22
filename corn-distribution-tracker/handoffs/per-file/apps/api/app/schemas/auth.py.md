# File Handoff: `apps/api/app/schemas/auth.py`

**Status:** TESTED  
**Primary owner:** Backend  
**File purpose:** Auth request/response schemas

## Responsibility
Define login, refresh/logout, me/user-safe responses, password reset and invitation schemas. Never accept client-selected role for self-registration.

## Contract and dependencies
domain role enums

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- Schema rejects invalid emails/password payload shapes; no secret fields leaked.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Strict auth schemas for login, refresh, logout, current user, password change/reset and invitation flows. `InvitationCreatedOut` returns the raw token exactly once to the creating admin.

**Verification (2026-10-22):** `make test-api` → 45 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 65 files; fresh PostgreSQL DB `alembic upgrade head → downgrade base → upgrade head` passed.

**Unresolved issues:** None known.
