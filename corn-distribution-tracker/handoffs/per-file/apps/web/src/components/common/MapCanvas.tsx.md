# File Handoff: `apps/web/src/components/common/MapCanvas.tsx`

**Status:** IMPLEMENTED
**Primary owner:** Frontend
**File purpose:** Shared MapLibre canvas with street/satellite basemaps and accessible markers

## Responsibility
Create and dispose a MapLibre map, apply the resolved basemap style, keep the MapLibre worker URL valid under Vite, switch between the built-in OpenStreetMap and Esri satellite layers, render typed markers as keyboard-focusable buttons when selection is supplied (otherwise labelled images), fit bounds when the point geometry changes, optionally recenter on the browser's current location after an explicit click, and show a caller-provided fallback if MapLibre cannot initialize. Does not fetch data or enforce authorization.

## Contract and dependencies
`lib/map.ts` for basemap resolution, layer ids and attribution; `maplibre-gl` and its worker asset; shared map CSS. Marker callbacks only update the owning screen's selected-site state. Geolocation is user-triggered only and never sent to the server by this component.

## Acceptance criteria
- Default OpenStreetMap streets render with visible attribution; Satellite switches to Esri imagery and its attribution.
- Marker selection does not recreate the map; geometry changes fit bounds without refitting on selection alone.
- The “My location” button is opt-in, requests geolocation only on click, and reports denial/failure without breaking the map.
- Map initialization failure renders the fallback instead of a blank container.
- No data fetching or permission decisions in this component.
- Typecheck/lint/build and browser smoke pass.

## Handoff back to integrator
Report: props exported, files changed, actual verification commands/results, configuration requirements and known limitations. Move status to `TESTED` only after a component test or equivalent browser test is committed and passing.

## Implementation summary

Added a shared `MapPoint`/`MapCanvas` interface used by the delivery-only admin map and evidence review. The map uses `buildMapStyle()` (OpenStreetMap streets + Esri satellite by default), explicitly sets the Vite-emitted MapLibre worker URL, keeps attribution visible, renders markers as real buttons when selectable, fits bounds only when point geometry changes, and falls back to caller content when the map cannot start. A Map/Satellite overlay switches layer visibility without recreating the map. The optional “My location” control requests browser geolocation only after a click, flies to the result and adds a temporary blue marker.

**Verification (2026-10-25):** `npx tsc -b --noEmit`, `npx eslint src --max-warnings=0`, `npm test` → 34 passed (5 files) and `npm run build` passed. Headless Chromium loaded 28 OSM street tiles and 15 Esri satellite tiles (all `200`), confirmed attribution switched between OSM and Esri, and recentered a mocked New Delhi geolocation on the satellite view with the “Your current location” marker. Browser smoke is not a committed automated test.

**Unresolved issues:** No unit/component test for MapLibre initialization (browser smoke only). Public OSM/Esri tiles are development/small-scale defaults; production must configure permitted providers.
