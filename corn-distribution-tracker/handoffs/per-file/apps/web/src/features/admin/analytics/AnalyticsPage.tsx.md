# File Handoff: `apps/web/src/features/admin/analytics/AnalyticsPage.tsx`

**Status:** IMPLEMENTED
**Primary owner:** Frontend
**File purpose:** Analytics and exports

## Responsibility
Show campaign/UTC-date-scoped KPI charts and tables for distributor/site performance and an audited CSV export using API formulas; label period vs current balance. Status/distributor/site filters are not exposed in the UI.

## Contract and dependencies
analytics API

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- Chart and table use matching server result/filter.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Campaign/date-scoped KPIs, accessible CSS bar charts and tables, and an audited CSV export via the shared download helper.

**Verification (2026-10-23):** `cd apps/web && npm test` → 23 passed (4 files); `npm run lint` → 0 errors/0 warnings; `npm run build` → tsc + Vite production build succeeded.

**Unresolved issues:** None known.
