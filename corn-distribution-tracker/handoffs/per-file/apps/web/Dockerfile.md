# File Handoff: `apps/web/Dockerfile`

**Status:** DEFERRED
**Primary owner:** DevOps / Lead Integrator
**File purpose:** Optional web container (not part of the supported native workflow).

## Responsibility
Build production assets with a multi-stage image and serve them using a minimal static server; set correct fallback routing/security headers via deployment config.

## Contract and dependencies
package scripts

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- Reproducible container build and health smoke test.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Multi-stage Node 22 build → nginx runtime, retained as optional packaging. VITE_* values are build args (public only); nginx serves the SPA and proxies `/api/` to the API. Healthcheck uses exec-form wget. The documented local workflow builds and serves the SPA with Vite instead.

**Verification (2026-10-23):** `cd apps/web && npm test` → 23 passed (4 files); `npm run lint` → 0 errors/0 warnings; `npm run build` → tsc + Vite production build succeeded.

**Unresolved issues:** Container build/runtime is deferred and outside the supported native workflow. The committed `nginx.conf` now targets a native same-host Django upstream (`127.0.0.1:8000`); if container packaging is revived, adjust its root/upstream for the container network.
