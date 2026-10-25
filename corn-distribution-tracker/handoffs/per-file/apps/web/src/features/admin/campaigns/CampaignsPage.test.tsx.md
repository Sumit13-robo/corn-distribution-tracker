# File Handoff: `apps/web/src/features/admin/campaigns/CampaignsPage.test.tsx`

**Status:** TESTED
**Primary owner:** Frontend
**File purpose:** Campaign site setup and optional-location tests

## Responsibility

Component coverage for the campaign-site flow:

- creating a campaign sends the entered site names (one per line) in the `sites` payload and de-duplicates case-insensitively;
- adding a site from the selected campaign sends only `name` and `campaign_id` (no coordinates);
- an existing name-only site exposes **Add location (optional)** and PATCHes latitude/longitude when the optional dialog is submitted.

## Contract and dependencies

Vitest, Testing Library, React Query and `ToastProvider`; the API client is mocked. No real network or personal data is used.

## Verification

`cd apps/web && npm test` → 37 passed across 6 files; `npm run typecheck`, `npm run lint` and `npm run build` pass.

## Unresolved issues

None known.
