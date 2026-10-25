# File Handoff: `apps/web/src/lib/map.ts`

**Status:** TESTED
**Primary owner:** Frontend
**File purpose:** Basemap configuration, basemap layer ids and map links

## Responsibility
Resolve `VITE_MAP_STYLE_URL` / `VITE_MAP_TILE_URL` / `VITE_MAP_SATELLITE_TILE_URL` into a MapLibre style, defaulting to OpenStreetMap streets plus Esri World Imagery satellite with the required attribution. Report whether the built-in basemap switch is available, and build validated OpenStreetMap and Google Maps viewer URLs for an exact coordinate. No secrets are read; all env values are public build-time configuration.

## Contract and dependencies
MapLibre `StyleSpecification`; Vite `import.meta.env`; `docs/ops/ENVIRONMENT_VARIABLES.md`.

## Acceptance criteria
- Empty configuration returns both raster sources with streets visible and satellite hidden.
- A full style URL takes precedence and disables the built-in basemap switch.
- Street and satellite tile URLs each override only their own default template.
- Invalid coordinates return safe provider home pages rather than broken deep links.
- Tests cover every case.

## Handoff back to integrator
Report exports, changed files and actual test results. Status is `TESTED` because `map.test.ts` passes.

## Implementation summary

Exports `OPENSTREETMAP_TILE_URL`, `OPENSTREETMAP_ATTRIBUTION`, `ESRI_WORLD_IMAGERY_TILE_URL`, `ESRI_WORLD_IMAGERY_ATTRIBUTION`, `BASEMAP_LAYER_IDS`, `BasemapId`, `hasBuiltInBasemaps()`, `buildMapStyle()`, `osmViewerUrl()` and `googleMapsViewerUrl()`. `buildMapStyle()` accepts injectable values for tests; production calls use the public Vite env values. Google Maps is a consumer link only and needs no API key.

**Verification (2026-10-25):** `cd apps/web && npm test` → 34 passed across 5 files, including 9 map tests; `npx tsc -b --noEmit` and `npx eslint src --max-warnings=0` passed; `npm run build` passed.

**Unresolved issues:** Public OSM/Esri tiles are not production-scale providers. Embedding Google Maps would require a key and billing.
