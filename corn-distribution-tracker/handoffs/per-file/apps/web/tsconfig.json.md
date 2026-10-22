# File Handoff: `apps/web/tsconfig.json`

**Status:** TESTED  
**Primary owner:** DevOps / Lead Integrator  
**File purpose:** TypeScript config

## Responsibility
Enable strict type checking, JSX, modern module resolution and consistent aliases; no blanket skip checks that hide application type errors.

## Contract and dependencies
web source structure

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- Typecheck passes with strict mode.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Strict TypeScript config (ES2022, bundler resolution, `noUncheckedIndexedAccess`, `verbatimModuleSyntax`) covering sources, tests, setup, Vite config, Playwright config and the E2E support files; `tsc -b` is clean.

**Verification (2026-10-22):** `npx tsc -b --noEmit` → clean (including E2E); `npm test` → 14 passed; `npm run test:e2e` → 8 passed; `npm run build` succeeded.

**Unresolved issues:** None known.
