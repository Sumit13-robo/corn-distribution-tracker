# File Handoff: `apps/web/src/components/layout/TopBar.tsx`

**Status:** IMPLEMENTED
**Primary owner:** Frontend
**File purpose:** Top bar

## Responsibility
Render page context, campaign selector when supported, current user, connectivity/sync status and profile/logout menu.

## Contract and dependencies
session; offline state

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- All controls functional; accessible menu.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Current user/role, online status and unsynced draft count, plus logout confirmation with keep-or-discard handling for offline drafts.

**Verification (2026-10-23):** `cd apps/web && npm test` → 39 passed (7 files); `npm run lint` → 0 errors/0 warnings; `npm run build` → tsc + Vite production build succeeded.

**Unresolved issues:** None known.

## Campaign-site update (2026-10-25)

Removed the `/sites` route title; `/sites` redirects to `/campaigns`. Verification: `npm run typecheck`, `npm run lint`, `npm test` (39 passed) and `npm run build`.
