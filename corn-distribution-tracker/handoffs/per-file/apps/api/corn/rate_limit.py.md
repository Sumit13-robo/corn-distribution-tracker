# File Handoff: `apps/api/corn/rate_limit.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Process-local rate limiting for authentication attempts

## Current implementation

Thread-safe, process-local sliding-window limits for login, password reset, invitation acceptance, evidence upload intents and delivery creation. `hit()` remains the atomic check-and-record primitive for actions where every request counts. `check()` and `record()` split the login path so the pre-hash gate can reject a blocked IP without consuming budget for successful sign-ins; only a wrong password or nonexistent account calls `record()`. `reset_for_tests()` clears the in-memory state between tests. Limits are per process and require a shared backend if the API is horizontally scaled.

## Verification

Backend: `make test-api` → 60 passed (including 13 successful logins in one window and the 10-failure lockout); `make lint-api` → all checks passed; `make typecheck-api` → no issues in 49 source files; migration check → no changes. Browser verification on 2026-10-23 confirmed the `429` `Retry-After` path renders an actionable message.

## Unresolved issues

None known. Docker image build/runtime remains unverified on this host (no Docker daemon).
