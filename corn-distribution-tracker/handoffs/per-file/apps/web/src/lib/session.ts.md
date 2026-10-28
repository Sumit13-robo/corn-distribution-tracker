# File Handoff: `apps/web/src/lib/session.ts`

**Status:** TESTED
**Primary owner:** Frontend
**File purpose:** Session state for Django cookie authentication.

## Current implementation

Module-level session state (`loading|authenticated|signed-out|error`), login, logout, current-user restore and subscriptions. The browser stores no access token; reload restores the server session via `GET /auth/me` using the HttpOnly `sessionid` cookie. Logout clears local state and draft handling is coordinated by the shell.

## Verification

Web suite 39 passed, Playwright session/reload test passed, 360 px audit clean.

## Unresolved issues

None known.
