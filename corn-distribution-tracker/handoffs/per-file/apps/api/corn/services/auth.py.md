# File Handoff: `apps/api/corn/services/auth.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Login, invitation, password reset/change, session revocation and account lifecycle

## Current implementation

Login, invitation, password reset/change, session revocation and account lifecycle. Login checks the per-IP failure window before password hashing, records a slot only when the password is wrong or the account does not exist, and leaves successful/inactive-account attempts out of the failure budget. Account-level lockout, generic credential errors, audit events and Django session creation are unchanged.

## Verification

Backend: `make test-api` → 60 passed (including the successful-login budget and locked-account retry-window tests); `make lint-api` → all checks passed; `make typecheck-api` → no issues in 49 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (8 passed).

## Unresolved issues

None known. Docker image build/runtime remains unverified on this host (no Docker daemon).
