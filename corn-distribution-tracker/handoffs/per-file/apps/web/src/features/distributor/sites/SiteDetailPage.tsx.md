# File Handoff: `apps/web/src/features/distributor/sites/SiteDetailPage.tsx`

**Status:** IMPLEMENTED
**Primary owner:** Frontend
**File purpose:** Assigned site detail

## Responsibility
Show expected location, assignment quantities, own history/status/review reasons and CTA to create update.

## Contract and dependencies
site/assignment/delivery APIs

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- No other distributor's private record is shown.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Site detail with target progress, recent deliveries and a new-delivery CTA.

**Verification (2026-10-23):** `cd apps/web && npm test` → 39 passed (7 files); `npm run lint` → 0 errors/0 warnings; `npm run build` → tsc + Vite production build succeeded.

**Unresolved issues:** None known.

## Name-only site update (2026-10-25)

Expected-location panel handles nullable site coordinates: it shows a clear notice instead of invalid `"null, null"` coordinates and no Google/OSM link is generated. Verification: `npm run typecheck`, `npm run lint`, `npm test` (39 passed, 7 files) and `npm run build` pass.

## Location-warning removal (2026-10-25)

The nullable-coordinate notice remains, but the page no longer describes distance/geofence checks or location warnings. A name-only site simply has no reference point; the distributor's own history shows captured/missing location only. Verification: `npm test` → 39 passed; typecheck/lint/build pass.
