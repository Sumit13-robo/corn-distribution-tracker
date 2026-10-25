# File Handoff: `apps/web/src/lib/api-client.test.ts`

**Status:** TESTED
**Primary owner:** Frontend
**File purpose:** API client session/CSRF tests.

## Current implementation

Covers session bootstrap, unsafe requests carrying `X-CSRFToken`, no bearer/refresh flow, structured error parsing, evidence URL handling and logout behavior with mocked fetch. Uses first-party session cookies.

## Verification

`npm test -- --run` → 23 passed across 3 files.

## Unresolved issues

None known.
