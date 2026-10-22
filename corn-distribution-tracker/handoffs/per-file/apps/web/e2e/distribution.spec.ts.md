# File Handoff: `apps/web/e2e/distribution.spec.ts`

**Status:** TESTED
**Primary owner:** QA / Frontend
**File purpose:** Critical distributor/reviewer browser workflow

## Responsibility
Prove the real SPA + API + PostgreSQL loop: session restore, role guard, evidence submission, private image rendering, approval with ledger posting, approved-record visibility, and honest offline queue/sync.

## Contract and dependencies
Playwright config/setup; public API seeded data; `e2e/support/credentials.ts`; docs for auth, offline sync, evidence and review semantics.

## Implementation summary
Five serial Chromium tests:
1. distributor login, HttpOnly refresh cookie, no token in localStorage, reload restores session, admin route denied;
2. 25 kg submission with a valid PNG, location capture at the site coordinates, photo evidence count;
3. admin opens the private evidence image (waits for real `naturalWidth`), approves and posts the movement;
4. distributor sees `Approved` plus the ledger movement;
5. offline submission stays `QUEUED` with an unchanged idempotency key, then becomes `SUBMITTED` only after reconnect and appears in history.

This suite caught two real cross-layer bugs: the missing `SiteOut` fields in the distributor assignment response (500) and location fixes not being persisted to the draft until submit. Regression coverage was added for both.

**Verification (2026-10-22):** `npm run test:e2e` → **7 passed** total (2 setup + these 5) against real FastAPI/PostgreSQL.

**Unresolved issues:** No real mobile-device, camera-permission or cross-browser run; Chromium only.
