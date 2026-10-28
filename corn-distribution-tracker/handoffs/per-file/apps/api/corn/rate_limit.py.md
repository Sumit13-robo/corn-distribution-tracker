# File Handoff: `apps/api/corn/rate_limit.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Process-local rate limiting for authentication attempts

## Current implementation

Thread-safe, process-local sliding-window limits for login, password reset, invitation acceptance, evidence upload intents and delivery creation. `hit()` remains the atomic check-and-record primitive for actions where every request counts. `check()` and `record()` split the login path so the pre-hash gate can reject a blocked IP without consuming budget for successful sign-ins; only a wrong password or nonexistent account calls `record()`. `reset_for_tests()` clears the in-memory state between tests. Limits are per process and require a shared backend if the API is horizontally scaled.

## Verification

Backend: `make test-api` → 98 passed (including 13 successful logins in one window and the 10-failure lockout); `make lint-api` → all checks passed; `make typecheck-api` → no issues in 51 source files; migration check → no changes. Browser verification on 2026-10-23 confirmed the `429` `Retry-After` path renders an actionable message.

## Unresolved issues

Process-local only: multiple Gunicorn workers or replicas each enforce their own counters. Use a shared Redis/cache limiter before horizontal scale-out. The bucket table is bounded to prevent unbounded memory growth.

## 2026-10-26 audit remediation

The process-local bucket table is now bounded and evicts expired/oldest entries. This fixes unbounded memory growth, but multi-worker deployments still need a shared limiter.

Verification for the current tree: 98 API tests, 39 web tests, 9 Playwright E2E tests, Ruff/mypy/migration/build gates clean. External provider/container/proxy evidence remains operator-owned.
