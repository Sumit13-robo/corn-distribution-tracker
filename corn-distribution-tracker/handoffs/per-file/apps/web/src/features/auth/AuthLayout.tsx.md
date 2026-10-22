# File Handoff: `apps/web/src/features/auth/AuthLayout.tsx`

**Status:** IMPLEMENTED
**Primary owner:** Frontend
**File purpose:** Shared split layout for public authentication screens.

## Current implementation

Provides the brand panel and compact mobile wordmark used by login, invitation/reset and password-change screens. Page copy states that email is not sent in this deployment and that an operator supplies reset links securely. Layout collapses without horizontal overflow and maintains visible focus.

## Verification

Covered by the web build/typecheck and the 360 px screenshot audit (`scrollWidth = 360` on public and authenticated routes).

## Unresolved issues

None known.
