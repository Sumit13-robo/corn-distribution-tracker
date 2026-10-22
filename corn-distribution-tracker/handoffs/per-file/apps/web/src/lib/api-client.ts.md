# File Handoff: `apps/web/src/lib/api-client.ts`

**Status:** TESTED
**Primary owner:** Frontend
**File purpose:** Typed API client over Django session auth and CSRF.

## Current implementation

Fetches JSON with same-origin credentials, reads the `csrftoken` cookie for unsafe methods and bootstraps it via `GET /auth/csrf` when necessary. A 401 clears session state and returns the caller to authentication; there is no refresh call/retry or bearer header. Adds request IDs and the uniform API error envelope, handles pagination/query serialization, protected evidence view URLs, CSV downloads and all domain endpoints.

## Verification

`npm test` → 18 passed (including session/CSRF client tests). `npx tsc -b --noEmit`, ESLint and production build pass.

## Unresolved issues

None known.
