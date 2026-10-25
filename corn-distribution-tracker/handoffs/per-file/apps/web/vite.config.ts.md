# File Handoff: `apps/web/vite.config.ts`

**Status:** TESTED
**Primary owner:** DevOps / Lead Integrator
**File purpose:** Vite config

## Responsibility
Configure app entry, dev proxy, test-compatible aliases and environment handling; keep secrets out of client bundle.

## Contract and dependencies
web environment

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- Production build succeeds and secret scan is clean.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

React plugin, dev server on 5173 with a same-origin `/api` proxy to :8000, Vitest jsdom configuration, and an explicit `src/**/*.test.*` include so Playwright specs are never collected by Vitest. Development `server.allowedHosts` includes `.trycloudflare.com` so a temporary HTTPS quick tunnel can provide the secure context required by phone geolocation; other hostnames still fail the Host check.

**Verification (2026-10-25):** `cd apps/web && npm test` → 34 passed (5 files); `npx tsc -b --noEmit` and `npx eslint src --max-warnings=0` passed; `npm run build` passed. HTTPS quick-tunnel smoke verified login and geolocation through this config.

**Unresolved issues:** A quick tunnel is public and temporary; do not use it for real data. Production should use a trusted HTTPS reverse proxy.
