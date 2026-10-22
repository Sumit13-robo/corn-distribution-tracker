# File Handoff: `apps/api/app/cli/create_admin.py`

**Status:** TESTED  
**Primary owner:** Backend  
**File purpose:** First-admin CLI

## Responsibility
Provide a one-shot secure command to create the first admin with an interactive password prompt or safe input path, hash the password and refuse unsafe duplicate/bootstrap behavior.

## Contract and dependencies
auth/security; user model; config

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- No public bootstrap route; secrets not echoed or logged.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

One-time admin bootstrap: refuses when an admin exists, validates email, reads the password via getpass or env indirection (`INITIAL_ADMIN_PASSWORD_ENV` names the variable), hashes with Argon2id and never prints/logs the secret.

**Verification (2026-10-22):** manual CLI smoke on a disposable PostgreSQL DB — first run created the admin, ensured settings/central account, and exited 0; a second run refused with “An administrator already exists” (exit 1). Backend suite: 45 passed; ruff/mypy clean.

**Unresolved issues:** No automated test for the interactive CLI; the non-interactive path was smoke-tested manually.
