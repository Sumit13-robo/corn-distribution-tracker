# File Handoff: `apps/web/src/app/providers.tsx`

**Status:** IMPLEMENTED
**Primary owner:** Frontend
**File purpose:** App providers

## Responsibility
Configure query client, session provider, theme/accessibility providers and global notification system; avoid caching private API data across user changes.

## Contract and dependencies
query client; session

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- Logout clears/re-scopes private cached data.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Query client provider, toast context, online/queue status banner, OfflineSyncManager (reconnect, interval, cross-tab storage changes only) and cache/session cleanup on logout. Exports ToastProvider for tests.

**Verification (2026-10-22):** `cd apps/web && npm test` → 18 passed (3 files); `npm run lint` → 0 errors/0 warnings; `npm run build` → tsc + Vite production build succeeded.

**Unresolved issues:** None known.
