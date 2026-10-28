# File Handoff: `apps/web/src/features/admin/map/DistributionMapPage.tsx`

**Status:** TESTED
**Primary owner:** Frontend
**File purpose:** Delivery-only admin map

## Current implementation

The admin map renders only distributor-recorded delivery locations returned by `GET /analytics/map-deliveries`. It plots `SUBMITTED` and `APPROVED` delivery records with a captured fix; rejected/cancelled claims are excluded by the API. Site reference coordinates, sites without deliveries and the admin's current position are not plotted, and the page has no “My location” control.

A campaign filter scopes the query. The synchronized list is keyboard-accessible and shows site code/name, distributor, status, quantity and submitted time. Selecting an entry highlights its marker and opens a drawer with site/distributor, quantity, submitted time, captured coordinates/accuracy, exact OpenStreetMap/Google Maps links and a link to `/evidence?record_id=…`. The MapLibre canvas keeps OpenStreetMap streets plus an Esri satellite switch by default (or `VITE_MAP_STYLE_URL` / tile overrides); if initialization fails, a labelled coordinate board positions the delivery points instead. The empty state explains that markers require a delivery with a captured location.

`MapCanvas` remains shared and supports an optional locate control, but this page does not enable it. The map payload never includes evidence URLs, and server authorization remains authoritative.

## Contract and dependencies

`docs/architecture/API_CONTRACT.md` (`/analytics/map-deliveries`), `docs/design/UX_SPEC.md`, `docs/design/SCREEN_SPECS.md`, `apps/web/src/lib/api-client.ts`, `apps/web/src/lib/query-client.ts`, `apps/web/src/types/domain.ts`, shared `MapCanvas`.

## Verification

`DistributionMapPage.test.tsx` (2 tests) proves the delivery list/map label, absence of the old “Sites in scope” list, drawer/link behavior and the no-delivery empty state. `npm run typecheck`, `npm run lint`, `npm test` (39 passed across 7 files), `npm run build` and `make test-e2e` (9 passed) pass.

## Unresolved issues

No committed browser test navigates to `/map` or verifies map-tile rendering of the retained Kolhapur point. Public OSM/Esri tiles are development/small-scale defaults; production must use permitted providers. Google Maps is a link-out, not an embedded provider.

## History

The earlier site-status map and pending-location drawer were replaced on 2026-10-25 so the page answers only where a distributor recorded a delivery.
