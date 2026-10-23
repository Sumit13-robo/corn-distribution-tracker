# File Handoff: `apps/web/src/features/auth/LoginPage.test.tsx`

**Status:** TESTED
**Primary owner:** Frontend
**File purpose:** Login failure-message and rate-limit UX tests

## Responsibility
Verify that credential failures stay generic while throttling and service outages produce actionable messages, and that `LoginPage` renders the message from a rejected sign-in.

## Contract and dependencies
Vitest, Testing Library, MemoryRouter, mocked `lib/session`, `ApiError` from `lib/api-client`, `LoginPage`/`loginErrorMessage`.

## Implementation summary

- `loginErrorMessage()` unit cases: generic `401`, `429` with a minutes window, `429` with a seconds window, network `TypeError`, and `503`.
- Component case: a rejected `login()` with `429` and `retry_after: 120` renders "Too many sign-in attempts. Try again in 2 minutes." and does not blame the password.
- `loginMock` is created with `vi.hoisted()` so the hoisted session mock can use it; `cleanup()` and `mockReset()` run after each test.

**Verification (2026-10-23):** `cd apps/web && npm test` → 23 passed (4 files); `npm run lint` → 0 errors/0 warnings; `npm run build` → tsc + Vite production build succeeded.

**Unresolved issues:** None known.
