# File Handoff: `apps/web/package.json`

**Status:** TESTED  
**Primary owner:** DevOps / Lead Integrator  
**File purpose:** Web scripts/dependencies

## Responsibility
Declare scripts for dev/build/lint/typecheck/test and pinned compatible dependencies; avoid deprecated packages.

## Contract and dependencies
stack spec

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- All documented commands exist and pass.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Scripts (dev/build/test/lint/typecheck/test:e2e) and pinned dependencies, including Playwright and `@types/node`. maplibre-gl 6.15 and Vitest 4.1 upgrades cleared npm audit advisories.

**Verification (2026-10-22):** `cd apps/web && npm test` → 14 passed (3 files); `npm run lint` → 0 errors/0 warnings; `npm run build` → tsc + Vite production build succeeded; `npm run test:e2e` → 7 passed; `npm audit` → 0 vulnerabilities.

**Unresolved issues:** None known.
