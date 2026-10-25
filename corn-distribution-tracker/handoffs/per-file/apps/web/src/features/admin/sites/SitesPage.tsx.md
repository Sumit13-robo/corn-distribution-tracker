# File Handoff: `apps/web/src/features/admin/sites/SitesPage.tsx`

**Status:** REMOVED
**Primary owner:** Frontend
**File purpose:** Removed standalone admin Sites page

## Removal (2026-10-25)

The file was deleted. Sites are now campaign-scoped and managed inside `apps/web/src/features/admin/campaigns/CampaignsPage.tsx`:

- campaign creation accepts optional site names in one transaction;
- the selected campaign shows a **Sites for this campaign** panel for adding more names;
- an optional latitude/longitude dialog lets an admin set or edit a site location later;
- the admin sidebar no longer links to `/sites`, and the SPA `/sites` route redirects to `/campaigns`.

The API resources `GET/POST /sites`, `PATCH /sites/{id}` and `POST /sites/{id}/deactivate` remain; only the standalone admin screen was removed. The distributor site detail page remains.

## Verification

`cd apps/web && npm run typecheck`, `npm run lint`, `npm test` (37 passed across 6 files) and `npm run build` pass. `make test-e2e` → 8 passed. `rg` confirms no remaining SPA links to `/sites` except the redirect itself.

## Unresolved issues

None known.
