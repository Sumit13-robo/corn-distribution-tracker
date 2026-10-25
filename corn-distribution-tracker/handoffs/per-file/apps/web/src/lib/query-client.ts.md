# File Handoff: `apps/web/src/lib/query-client.ts`

**Status:** IMPLEMENTED
**Primary owner:** Frontend
**File purpose:** Server state cache

## Responsibility
Create query defaults, stale times and safe query-key factory. Invalidate metrics/sites/balances after mutations; clear private queries on logout.

## Contract and dependencies
api client

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- No stale private data on account switch.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Shared QueryClient defaults (no retry on 4xx, bounded transient retry) and the centralized query-key factory used by every screen. Added a `site` detail key so evidence review can load the selected site's current coordinates for the location map.

**Verification (2026-10-25):** `npx tsc -b --noEmit`, `npx eslint src --max-warnings=0`, `npm test` → 34 passed (5 files) and `npm run build` passed.

**Unresolved issues:** None known.

## Campaign-site update (2026-10-25)

`queryKeys.sites` includes `campaign_id` so switching the selected campaign does not reuse another campaign's site list. Verification: `npm run typecheck`, `npm test` (37 passed) and `npm run build`.

## Delivery-map update (2026-10-25)

Added `queryKeys.mapDeliveries(campaignId, distributorId)`. Evidence review invalidation now clears `analytics-map-deliveries` after approve/reject/cancel so delivery-point status colours refresh. Verification: `npm run typecheck`, `npm test` (39 passed) and `npm run build`.
