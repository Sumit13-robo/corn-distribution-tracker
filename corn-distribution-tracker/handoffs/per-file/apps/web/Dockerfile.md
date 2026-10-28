# File Handoff: `apps/web/Dockerfile`

**Status:** IMPLEMENTED
**Primary owner:** DevOps / Lead Integrator
**File purpose:** Multi-stage web container with nginx runtime configuration and healthcheck.

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

**Verification (2026-10-26):** `cd apps/web && npm test` → 39 passed (7 files); `npm run lint` → 0 errors/0 warnings; `npm run build` → tsc + Vite production build succeeded. Static multi-stage Dockerfile checks pass. The container now copies `nginx.docker.conf`, whose upstream is `api:8000` and whose static root is `/usr/share/nginx/html`; the native `nginx.conf` keeps `127.0.0.1:8000`.

**Unresolved issues:** Container build/runtime is deferred; no Docker/Podman/Buildah or nginx binary is available in this workspace.

## 2026-10-26 audit remediation

The runtime image now copies `nginx.docker.conf`, so the container proxy targets `api:8000` instead of loopback. Static checks pass; no container runtime is available.

Verification for the current tree: 98 API tests, 39 web tests, 9 Playwright E2E tests, Ruff/mypy/migration/build gates clean. External provider/container/proxy evidence remains operator-owned.
