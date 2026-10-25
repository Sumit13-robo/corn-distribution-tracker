# File Handoff: `apps/web/src/lib/map.test.ts`

**Status:** TESTED
**Primary owner:** Frontend
**File purpose:** Map configuration and map link tests

## Responsibility
Verify the default OpenStreetMap + Esri satellite style and attributions, full-style precedence, street/satellite template overrides, built-in-switch availability, exact-coordinate OSM/Google Maps links and invalid-coordinate fallbacks.

## Contract and dependencies
`vitest`; `lib/map.ts`.

## Acceptance criteria
- Nine tests cover default layers, precedence, both overrides, switch availability, valid links and invalid links.
- Tests make no network requests.

## Handoff back to integrator
No known issues.

## Implementation summary

Added nine Vitest cases for basemap/tile resolution, built-in switch availability, and OpenStreetMap/Google Maps link helpers.

**Verification (2026-10-25):** `cd apps/web && npm test` → 34 passed across 5 files (9 map tests).

**Unresolved issues:** None known.
