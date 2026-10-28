# File Handoff: `apps/web/src/features/admin/shared/flags.tsx`

**Status:** TESTED
**Primary owner:** Frontend
**File purpose:** Shared non-location evidence-integrity and captured/missing location UI

## Responsibility

Provide one place to render evidence-integrity flag labels/tones, filter legacy location flags from admin warnings, and label a device fix **Captured** or **Missing** without implying a warning.

## Implementation summary

- `integrityFlagList` filters `GPS_MISSING`, `GPS_STALE`, `GPS_LOW_ACCURACY`, `OUTSIDE_GEOFENCE`, `EXIF_GPS_MISMATCH` and `LOCATION_EXCEPTION` from warnings; only duplicate hash, capture-time mismatch and unexpected file type remain.
- `hasIntegrityFlags`, `locationCaptureLabel` and the shared `FlagList`/status helpers are used by evidence review, dashboard, map, site and submission screens.
- Location accuracy/coordinates are neutral context; a captured fix is never shown as an exception.

## Verification

`npm test` → 39 passed across 7 files; `npm run typecheck` and `npm run lint` pass; `npm run build` passes. Component/API tests and manual review cover captured/missing and integrity-only warning behavior.

## Unresolved issues

No dedicated component test for the filtering helper; behavior is covered indirectly by page tests and manual smoke.
