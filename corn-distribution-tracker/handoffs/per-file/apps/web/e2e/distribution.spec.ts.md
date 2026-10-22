# File Handoff: `apps/web/e2e/distribution.spec.ts`

**Status:** TESTED
**Primary owner:** QA / Frontend
**File purpose:** Critical distributor/reviewer browser workflow

## Responsibility
Prove the real SPA + API + PostgreSQL loop: session restore, role guard, evidence submission, private image rendering, approval with ledger posting, approved-record visibility, and honest offline queue/sync.

## Contract and dependencies
Playwright config/setup; public API seeded data; `e2e/support/credentials.ts`; docs for auth, offline sync, evidence and review semantics.

## Implementation summary
Six serial Chromium tests:
1. distributor login, HttpOnly refresh cookie, no token in localStorage, reload restores session, admin route denied;
2. 25 kg submission with a valid PNG, location capture at the site coordinates, photo evidence count;
3. admin opens the private evidence image (waits for real `naturalWidth`), approves and posts the movement;
4. distributor sees `Approved` plus the ledger movement;
5. offline submission stays `QUEUED` with an unchanged idempotency key, then becomes `SUBMITTED` only after reconnect and appears in history;
6. distributor workspace remains usable at a 360 px viewport with no horizontal page overflow.

This suite caught three real UI/contract defects: the missing `SiteOut` fields in the distributor assignment response (500), location fixes not being persisted to the draft until submit, and horizontal overflow in the 360 px header/navigation. Regression coverage was added for all three. Table assertions target the exact quantity cell so date/timestamp text cannot satisfy a substring match.

**Verification (2026-10-22):** `npm run test:e2e` → **8 passed** total (2 setup + these 6) against real FastAPI/PostgreSQL.

**Unresolved issues:** No real mobile-device, camera-permission or cross-browser run; Chromium only.
