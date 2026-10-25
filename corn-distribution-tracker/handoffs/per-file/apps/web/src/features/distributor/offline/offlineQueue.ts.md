# File Handoff: `apps/web/src/features/distributor/offline/offlineQueue.ts`

**Status:** TESTED
**Primary owner:** Frontend
**File purpose:** Offline draft queue

## Responsibility
Persist drafts and idempotency keys, queue/retry safely, surface state changes, scope data to user and clean up/disclose drafts on logout. Never label local queue as submitted.

## Contract and dependencies
offline sync spec; API client

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- Lost-response retry, reload, account switch and conflict tests.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

User-scoped localStorage drafts (`corn-tracker:drafts:v1:{userId}`) with persisted idempotency keys, LOCAL_DRAFT→QUEUED→UPLOADING→SUBMITTED transitions, IndexedDB photo store with memory fallback, requeue/retry/remove, submitted cleanup and cross-tab change notifications.

**Verification (2026-10-23):** `cd apps/web && npm test` → 23 passed (4 files); `npm run lint` → 0 errors/0 warnings; `npm run build` → tsc + Vite production build succeeded.

**Unresolved issues:** None known.

## Location-warning removal (2026-10-25)

Obsolete `GEO_VALIDATION`/`LOCATION_EXCEPTION` error mapping was removed; queued drafts no longer surface location-threshold text. Draft/idempotency/photo persistence behavior is unchanged. Verification: `npm test` → 37 passed.
