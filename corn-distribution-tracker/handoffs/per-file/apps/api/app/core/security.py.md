# File Handoff: `apps/api/app/core/security.py`

**Status:** TESTED  
**Primary owner:** Backend  
**File purpose:** Security primitives

## Responsibility
Implement password hashing/verification, short-lived access tokens, refresh token hashing/rotation helpers, safe token claims, and any CSRF/Origin primitives required by chosen session design. Avoid storing reusable raw refresh tokens.

## Contract and dependencies
config.py; security section

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- Unit tests for hash verify, expiry, token/session rotation edge cases.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Argon2id password hashing/verification, HS256 access JWTs (`sub`, `role`, `jti`, expiry), refresh and invitation/reset token generation with HMAC-SHA256 digests, constant-time digest comparison and cookie helpers.

**Verification (2026-10-22):** `make test-api` → 46 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 65 files; fresh PostgreSQL DB `alembic upgrade head → downgrade base → upgrade head` passed.

**Unresolved issues:** None known.
