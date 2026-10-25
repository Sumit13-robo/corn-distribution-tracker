# File Handoff: `apps/web/src/features/admin/settings/SettingsPage.tsx`

**Status:** TESTED
**Primary owner:** Frontend
**File purpose:** Organization settings (timezone, unit/bag, capture-time drift) and audit access

## Responsibility

Expose implemented organization settings only: timezone, default display unit, kg-per-bag factor and capture-time drift. Audit history is a separate screen. Require confirmation/reason for sensitive changes.

## Implementation summary

The geofence radius, GPS accuracy and location-age inputs were removed because location no longer gates or warns. The backend retains those fields for schema/API compatibility but they are legacy. The form still validates units/bag factor and capture-time drift and shows save/error states.

## Verification

`npm test` → 37 passed across 6 files; `npm run typecheck`, `npm run lint` and `npm run build` pass; `make test-e2e` → 8 passed.

## Unresolved issues

Legacy location settings can still be accepted by the API for compatibility; the UI intentionally does not expose them.
