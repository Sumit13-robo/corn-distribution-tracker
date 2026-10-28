# File Handoff: `apps/web/src/features/auth/LoginPage.tsx`

**Status:** TESTED
**Primary owner:** Frontend
**File purpose:** Login page

## Responsibility
Build responsive login, validation, show/hide password, loading/error states and reset link; no public signup or client role selection.

## Contract and dependencies
session; FormField

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- Valid/invalid login and loading UI test.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Email/password login with safe error display, redirect-on-success and a link to the reset flow. `loginErrorMessage()` keeps credential failures generic but reports `429` with the server's retry window, `5xx`/network outages as temporary unavailability, and `403` as an expired sign-in session.

**Verification (2026-10-23):** `cd apps/web && npm test` → 39 passed (7 files, including the new login-message tests); `npm run lint` → 0 errors/0 warnings; `npm run build` → tsc + Vite production build succeeded. Browser check with a live `429` confirmed `Too many sign-in attempts. Try again in 5 minutes.`

**Unresolved issues:** None known.
