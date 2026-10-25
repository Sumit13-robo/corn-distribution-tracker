# File Handoff: `apps/web/src/lib/api-client.ts`

**Status:** TESTED
**Primary owner:** Frontend
**File purpose:** Typed API client over Django session auth and CSRF.

## Current implementation

Fetches JSON with same-origin credentials, reads the `csrftoken` cookie for unsafe methods and bootstraps it via `GET /auth/csrf` when necessary. A 401 clears session state and returns the caller to authentication; there is no refresh call/retry or bearer header. Adds request IDs and the uniform API error envelope, handles pagination/query serialization, protected evidence view URLs, CSV downloads and all domain endpoints.

## Verification

`npm test` → 23 passed (including session/CSRF client tests). `npx tsc -b --noEmit`, ESLint and production build pass.

## Unresolved issues

None known.

## Campaign-site update (2026-10-25)

Site list filters include `campaign_id`; `createSite` accepts an optional campaign and name-only payload; `updateSite` accepts an optional/cleared location. Verification: `npm run typecheck`, `npm run lint`, `npm test` (37 passed, 6 files) and `npm run build` pass.

## Delivery-map update (2026-10-25)

Added `api.mapDeliveries(filters)` for `GET /analytics/map-deliveries`, returning typed `MapDeliveryOut[]`. The legacy `mapSites` method remains for API compatibility but has no screen consumer. Verification: `npm run typecheck`, `npm run lint`, `npm test` (39 passed, 7 files) and `npm run build` pass.
