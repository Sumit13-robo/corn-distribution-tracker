# File Handoff: `apps/web/src/features/admin/evidence/EvidenceReviewPage.tsx`

**Status:** TESTED
**Primary owner:** Frontend
**File purpose:** Evidence review UI with neutral location context and non-location integrity flags

## Responsibility

Show the pending queue, authorized private image, site/distributor/quantity/time, captured coordinates/accuracy (or **Missing**), a street/satellite map when a fix exists, exact OpenStreetMap/Google Maps links, image hash/duplicate status, non-location integrity flags and review history. Approve/reject/cancel with clear stock-posting warnings.

## Implementation summary

- Location is shown as **Captured** or **Missing**; coordinates and reported accuracy are neutral context.
- The former distance card, geofence copy and GPS-quality warnings were removed. A name-only site simply has no site marker; no distance/geofence explanation is required.
- Legacy location flags are filtered from the warning list. Only `DUPLICATE_IMAGE_HASH`, `CAPTURE_TIME_MISMATCH` and `UNEXPECTED_FILE_TYPE` require an override reason. An exceeded assignment target also requires a reason.
- Approval remains manual and can happen for any recorded place; the server posts the stock movement atomically.
- Existing map links and the site's current-coordinate marker remain for context; previous/next review navigation is not implemented.

## Verification

`npm test` → 37 passed across 6 files; `npm run typecheck`, `npm run lint` and `npm run build` pass; `make test-e2e` → 8 passed. Backend tests prove missing/far/stale/inaccurate fixes approve without a location exception.

## Unresolved issues

No committed browser/component test asserts the absence of location warnings on this page. The site marker is the site's current coordinate, not a historical snapshot. Google Maps is a link-out, not an embedded provider.

## Delivery-map invalidation (2026-10-25)

Approve/reject/cancel now also invalidates `analytics-map-deliveries`, so the delivery-only admin map refreshes status colours after review. Verification: `npm test` (39 passed, 7 files), `npm run typecheck` and `npm run lint` pass.
