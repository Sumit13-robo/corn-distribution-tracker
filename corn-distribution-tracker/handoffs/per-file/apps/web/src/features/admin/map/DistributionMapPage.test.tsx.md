# File Handoff: `apps/web/src/features/admin/map/DistributionMapPage.test.tsx`

**Status:** TESTED
**Primary owner:** Frontend/QA
**File purpose:** Delivery-only map component tests

## Responsibility

Render `DistributionMapPage` with mocked `listCampaigns`/`mapDeliveries` and a stubbed `MapCanvas`. The tests assert that:

- only a delivery record is listed and plotted, with site/distributor/quantity/status context;
- the removed “Sites in scope” site list is absent;
- selecting a delivery opens its drawer and builds `/evidence?record_id=…`;
- an empty delivery payload shows the explanation instead of an empty map.

The fixture is synthetic and contains no real personal data or geotagged photo.

## Contract and dependencies

`docs/architecture/API_CONTRACT.md` (`/analytics/map-deliveries`), `docs/design/UX_SPEC.md`, `DistributionMapPage.tsx`, `MapDeliveryOut`.

## Verification

`npm test -- --run src/features/admin/map/DistributionMapPage.test.tsx` → 2 passed; full web suite → 39 passed across 7 files; `npm run typecheck` and `npm run lint` pass.

## Unresolved issues

The test stubs `MapCanvas`, so it does not exercise MapLibre tile loading or WebGL fallback. Browser smoke remains the evidence for map rendering; no committed Playwright test visits `/map`.
