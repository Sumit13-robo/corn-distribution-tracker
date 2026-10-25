# Frontend Agent Handoff

## Own
`apps/web/**`. Use `API_CONTRACT.md` as the source of truth; if backend contract lacks a response field, raise it with lead/backend rather than hardcoding fake data.

## Sequence
1. Session/API/query foundation and router guards.
2. Design tokens and shared layout/form/table/status/error components.
3. Login and Admin shell/navigation.
4. Admin overview, map, sites, distributors, inventory, evidence review, analytics/settings.
5. Distributor mobile dashboard, assigned sites, detail, delivery/photo/GPS workflow, history and offline drafts.
6. Accessibility/responsive QA and component/E2E tests.

## Hard gates
- No mock KPI values in production routes.
- Do not report server submission success until server acknowledgement.
- Do not store session or CSRF secrets in localStorage.
- Clear private query cache on logout/account switch.
- Any file/photo preview must use authorized API or upload state; never a guessed public bucket URL.
- Location permission prompt starts only after user action and clearly explains purpose.
- Show pending vs approved as different states/quantities.

## Report
List pages completed, endpoints consumed, keyboard/mobile checks, tests/build results, and missing API contract fields.

## Final verification (2026-10-23)
All planned screens and the offline delivery flow are implemented. 23 Vitest tests across 4 files and 8 Playwright E2E tests pass; the browser flow covers session restore, photo/geolocation submission, evidence review/approval, approved history, offline QUEUED→SUBMITTED sync and a 360 px viewport check. Browser E2E also exposed and drove fixes for the assignment nested-site response, immediate location persistence and mobile header/navigation overflow. The map legend now uses the API's actual site statuses (`COMPLETE`, `PENDING`, `IN_PROGRESS`, `NO_ACTIVITY`).

## Map/location update (2026-10-25)
MapLibre now provides OpenStreetMap streets plus an Esri World Imagery satellite switch (no key), a user-triggered “My location” control, and exact OpenStreetMap/Google Maps links for every site/reported location. `VITE_MAP_STYLE_URL` still selects a full public style; `VITE_MAP_TILE_URL` and `VITE_MAP_SATELLITE_TILE_URL` override the built-in raster templates. Site selection opens a drawer with a reported-location map, and evidence review shows the distributor-reported fix against the site's current coordinates. Google Maps is generally the most accurate consumer map in India, but embedding it needs a key and billing, so the build uses satellite + Google links rather than pretending OSM/Esri is Google. The shared `MapCanvas` also fixes the Vite/MapLibre worker URL. `npx tsc -b --noEmit`, `npx eslint src --max-warnings=0`, `npm test` (34 passed, 5 files, 9 map tests) and `npm run build` pass. Headless Chromium loaded 28 OSM and 15 Esri tiles (all `200`), switched attribution, recentered on a mocked New Delhi position and found the expected Google Maps links. The demo sites were later removed by the 2026-10-25 cleanup; no real India location data was added. OSM/Esri public tiles are development/small-scale defaults; production must use permitted providers. No committed map-specific component test yet (browser smoke only).

## Phone/HTTPS location update (2026-10-25)

Phone browsers expose geolocation only in a secure context. The HTTP LAN URL can load the distributor UI and accept login, but GPS capture is blocked even when the site permission says “Allow”; that was the reported “access denied” symptom. `useDeviceLocation` now checks `window.isSecureContext === false` and shows explicit HTTPS guidance instead of calling the browser API and surfacing a misleading denial. The dev Vite config allows `.trycloudflare.com` hosts for a temporary HTTPS quick tunnel, and the phone flow was verified end-to-end through that tunnel: Amina login, assigned sites, delivery page, and a mocked Delhi fix captured as `28.613900, 77.209000 ±12.0 m` with no permission error. This is a development workaround; real deployments should use a trusted HTTPS reverse proxy, not a public quick tunnel. A 7.0 MB phone-style JPEG upload also returned `204` after the backend raw-body ceiling fix. Web checks: `npx tsc -b --noEmit`, `npx eslint src --max-warnings=0`, `npm test` → 34 passed across 5 files. Browser smoke and tunnel verification are not committed automated tests.

### Location policy update (2026-10-25)

The phone-capture investigation originally surfaced `GPS_MISSING` and `OUTSIDE_GEOFENCE` on demo records. The product policy has since been changed: location is supporting metadata only. The delivery form now shows whether a fix was captured plus coordinates/accuracy, but no distance, geofence, GPS-quality or “outside geofence” warning. `useDeviceLocation` tells a distributor that a denied permission still allows submission. Admin review labels a record **Captured** or **Missing** and filters legacy location flags from warnings; only duplicate hash, capture-time mismatch and unexpected file type remain. The old demo records discussed during debugging were deleted in the scoped development cleanup.

The two earlier UI fixes remain: a saved draft fix survives reload/submit and the form no longer falsely says a location is missing. **Verification:** the full web suite and a phone HTTPS tunnel smoke are recorded below.

## Campaign-scoped sites (2026-10-25)

The standalone admin **Sites** page and sidebar item were removed; `/sites` redirects to `/campaigns`. Campaign creation now accepts optional site names (one per line), and the selected campaign shows a site panel where an admin can add further name-only sites and optionally set or edit latitude/longitude later. The assignment site selector is limited to the selected campaign and displays names, not generated codes. Name-only sites have no map marker; device GPS is still stored when available, but location quality never warns or blocks.

`SiteOut` now includes `campaign_id` and nullable coordinates; `CampaignIn` accepts `sites`; the evidence review and distributor site detail handle missing site coordinates. Added `CampaignsPage.test.tsx` coverage for campaign-dialog site names, name-only site add and optional location later.

**Verification (2026-10-25):** `npm run typecheck` → passed; `npm run lint` → 0 errors/0 warnings; `npm test` → **37 passed across 6 files**; `npm run build` → passed (app JS 520.67 kB gzip 156.03 kB, CSS 104.49 kB; existing large-chunk warning); `make test-e2e` → **8 passed**.

**Unresolved issues:** Clearing a site location is API-supported but not exposed in the UI; site coordinates are entered manually (no map picker). No committed browser test opens the new campaign-site panel, though component tests cover its API calls. OSM/Esri public tiles remain development/small-scale defaults.


## Location-warning removal (2026-10-25)

- `EvidenceReviewPage` no longer renders a distance card, geofence copy or geo-status warnings. Location is **Captured**/**Missing**, with coordinates/accuracy and the existing map for context. Evidence flags are filtered through `integrityFlagList`; the approval override helper is limited to evidence integrity or an exceeded target.
- `AdminDashboardPage`, `DistributionMapPage`, `SiteDetailPage`, `MySubmissionsPage`, `DeliverySubmissionPage`, `CampaignsPage` and `SettingsPage` no longer show distance, geofence radius, GPS thresholds or location warnings. Settings now edits timezone/unit/bag/capture-time drift only; legacy geofence/accuracy/age fields remain in the API/schema for compatibility.
- `shared/flags.tsx` filters legacy location flags (`GPS_*`, `OUTSIDE_GEOFENCE`, `EXIF_GPS_MISMATCH`, `LOCATION_EXCEPTION`) and exposes captured/missing labels. `offlineQueue` no longer maps obsolete `GEO_VALIDATION`/`LOCATION_EXCEPTION` errors to location text.
- Development data was reduced to the Kolhapur campaign/site, Amina's assignment and approved 1 kg record, the minimum funding ledger chain and all three logins; Juba demo records/sites/stock and newer phone submissions were deleted after a database/private-storage backup. This does not alter any code contract.
- **Verification (2026-10-25):** `npm run typecheck` passed; `npx eslint src --max-warnings=0` passed; `npm test` → **37 passed across 6 files**; `npm run build` passed; `make test-e2e` → **8 passed**. The app is served by Django on `127.0.0.1:8000` and Vite on `127.0.0.1:5173`; the quick tunnel remains a temporary development ingress.
- **Unresolved issues:** no committed browser test specifically asserts the absence of location warnings; component/API tests and manual smoke cover it. Public OSM/Esri tiles remain development/small-scale defaults.

## Delivery-only admin map (2026-10-25)

`DistributionMapPage` now plots only distributor-recorded delivery locations. It calls the new `api.mapDeliveries()` endpoint and shows a synchronized delivery list with site code/name, distributor, status, quantity and submitted time. The campaign filter still scopes the query. Site reference coordinates, sites without deliveries and the admin “My location” control were removed from this page; rejected/cancelled claims are excluded by the API. Selecting a delivery opens a drawer with site/distributor, quantity, submitted time, captured coordinates/accuracy, OpenStreetMap/Google Maps links and a link to `/evidence?record_id=…`. The empty state explains that markers require a delivery with a captured location. The fallback coordinate board now positions delivery points, not sites. `queryKeys.mapDeliveries` was added, and evidence approve/reject/cancel invalidates `analytics-map-deliveries` so status colours update.

Added `DistributionMapPage.test.tsx` (2 tests) covering the delivery-only list/map label, removal of the old “Sites in scope” list, drawer/link behavior and the no-delivery empty state. The Playwright workflow now also signs in as admin after approval, opens `/map`, asserts the approved E2E record is the delivery point, verifies the map pin and drawer coordinates/evidence link, and asserts no site list is rendered. **Verification:** `npm run typecheck` passed; `npm run lint` passed; `npm test` → **39 passed across 7 files**; `npm run build` passed; `make test-e2e` → **9 passed** (2 setup + 7 workflow). Headless Chromium against the live dev stack rendered the current two approved Kolhapur records as two list entries and two map pins, opened the drawer with coordinates/map/evidence links, showed no site list, and logged no console errors or non-tile request failures. Public OSM/Esri tiles remain development/small-scale defaults; map-tile rendering itself is not asserted by the E2E (markers are).
