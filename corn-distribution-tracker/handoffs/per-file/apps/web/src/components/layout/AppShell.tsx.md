# File Handoff: `apps/web/src/components/layout/AppShell.tsx`

**Status:** IMPLEMENTED  
**Primary owner:** Frontend  
**File purpose:** Role-aware layout

## Responsibility
Render responsive sidebar/topbar/content slot, campaign context when applicable, profile/logout and offline/network indicator. Choose admin vs distributor nav based on resolved role.

## Contract and dependencies
layout components; permissions

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- Responsive route smoke test; keyboard navigation.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Role-derived navigation shell with skip link, responsive sidebar/topbar, offline banner and routed outlet.

**Verification (2026-10-22):** `cd apps/web && npm test` → 13 passed (3 files); `npm run lint` → 0 errors/0 warnings; `npm run build` → tsc + Vite production build succeeded.

**Unresolved issues:** None known.
