# File Handoff: `apps/api/app/core/config.py`

**Status:** TESTED  
**Primary owner:** Backend  
**File purpose:** Typed settings

## Responsibility
Load environment using typed settings; distinguish development/test/production; validate required secrets, URLs, cookie/CORS settings, upload limits and geo thresholds; fail fast on unsafe production defaults.

## Contract and dependencies
ENVIRONMENT_VARIABLES.md

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- Settings tests for missing/unsafe production config.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Typed pydantic-settings configuration for DB, auth, cookies, storage, geo defaults and organization defaults, including environment parsing helpers. `assert_secure_settings()` makes production/staging fail startup on placeholder secrets, insecure cookies, wildcard CORS with credentials or local/missing S3 configuration; development/test keep documented defaults. Covered by four tests in `tests/test_config_security.py`.

**Verification (2026-10-22):** `make test-api` → 45 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 65 files; fresh PostgreSQL DB `alembic upgrade head → downgrade base → upgrade head` passed.

**Unresolved issues:** None known.
