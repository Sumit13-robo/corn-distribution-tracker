# File Handoff: `apps/web/src/features/distributor/deliveries/MySubmissionsPage.tsx`

**Status:** IMPLEMENTED
**Primary owner:** Frontend
**File purpose:** Distributor submission history

## Responsibility
List only current distributor submissions with pending/approved/rejected state, quantity, evidence status, review reason and expandable detail.

## Contract and dependencies
delivery API; permissions

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- Own-record scope and status clarity tested.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Submission history with a status filter, expandable review details and per-evidence viewing via short-lived URLs. There is no date filter or pagination control.

**Verification (2026-10-23):** `cd apps/web && npm test` → 23 passed (4 files); `npm run lint` → 0 errors/0 warnings; `npm run build` → tsc + Vite production build succeeded.

**Unresolved issues:** None known.

## Location-warning removal (2026-10-25)

History shows location as captured/missing without distance, geofence or GPS-quality warnings; legacy location flags are filtered. Status/review reason/evidence behavior is unchanged. Verification: `npm test` → 37 passed; typecheck/lint/build pass.
