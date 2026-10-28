# File Handoff: `apps/web/nginx.conf`

**Status:** IMPLEMENTED
**Primary owner:** DevOps/Lead
**File purpose:** SPA server with same-origin API proxy.

## Current implementation

Serves the built SPA with history fallback, caches hashed assets, adds CSP (`frame-ancestors 'none'`), COOP, frame and referrer headers, and proxies `/api/` to a native Django/Gunicorn upstream at `127.0.0.1:8000`. It overwrites `X-Forwarded-For`/`X-Forwarded-Proto` rather than appending client-supplied values. The container-specific variant is `nginx.docker.conf`. Same-origin API calls keep the Django `sessionid` cookie first-party; `/api/v1/auth/csrf` supports explicit CSRF bootstrap.

## Verification

Static nginx checks pass (balanced config, SPA root, upstream, API proxy, CSP/COOP/frame headers, overwritten forwarding headers). Reverse-proxy runtime was not exercised. Native Django + Vite path verified.

## Unresolved issues

Reverse-proxy runtime remains deployment-specific; no nginx binary is available in this workspace.

## 2026-10-26 audit remediation

Added CSP/COOP/frame/referrer headers and overwrite (not append) forwarding headers; native upstream remains loopback.

Verification for the current tree: 98 API tests, 39 web tests, 9 Playwright E2E tests, Ruff/mypy/migration/build gates clean. External provider/container/proxy evidence remains operator-owned.
