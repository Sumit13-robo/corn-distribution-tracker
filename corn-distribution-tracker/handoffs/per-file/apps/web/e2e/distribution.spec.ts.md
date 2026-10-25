# File Handoff: `apps/web/e2e/distribution.spec.ts`

**Status:** TESTED
**Primary owner:** QA/Frontend
**File purpose:** Critical distributor/reviewer browser workflow.

## Current implementation

Serial Playwright tests against the real Django/DRF API, PostgreSQL and SPA:

1. distributor session-cookie login, reload restore, no browser token storage, and server role guard;
2. photo plus device-location submission with six-decimal coordinates;
3. admin evidence review and approval that posts the ledger movement;
4. admin delivery map shows the approved record as a delivery point/pin with no site list, opens the drawer with exact coordinates and an evidence link;
5. distributor sees the approved record and its ledger movement;
6. offline submission stays QUEUED and syncs the same idempotency key when connectivity returns;
7. distributor workspace has no horizontal overflow at 360 px.

The identity assertion targets the current top-bar structure (`E2E Distributor` plus the email in the element title), not the removed combined text.

## Verification

`npm run test:e2e` → **9 passed** (2 setup + 7 workflow) after a clean database recreation. `1 image` and six-decimal coordinates are asserted against the actual UI. The map assertion checks list data, one `.map-pin`, drawer coordinates and the evidence link; it does not load or assert external tile imagery.

## Unresolved issues

Local-only: needs PostgreSQL with CREATEDB, the repo virtualenv and Chromium. It does not replace real-device or assistive-technology testing, and it does not force/test the WebGL coordinate-board fallback.
