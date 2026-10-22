# File Handoff: `apps/web/e2e/setup.spec.ts`

**Status:** TESTED
**Primary owner:** QA / Backend integration
**File purpose:** E2E data seeding through public APIs

## Responsibility
Create the synthetic campaign, site, distributor invitation/account, assignment, central receipt and distributor allocation, then verify the generated distributor credentials against the real login endpoint.

## Contract and dependencies
`e2e/support/credentials.ts`; `e2e/support/config.ts`; public API contracts for auth, campaigns, sites, users, assignments and inventory. No direct SQL writes.

## Implementation summary
Admin login → create active campaign and site at the synthetic Juba coordinates → invite/accept distributor → create 500 kg assignment → receive 2000 kg central stock → allocate 500 kg to the distributor. Every response is checked and failures include status/body. A second setup test proves the generated distributor password works and the role is `DISTRIBUTOR`.

**Verification (2026-10-22):** both setup tests passed repeatedly as part of the 7-test E2E run.

**Unresolved issues:** None known. All identities/data are synthetic and the database is recreated each run.
