# File Handoff: `apps/web/nginx.docker.conf`

**Status:** IMPLEMENTED
**Primary owner:** Frontend/DevOps
**File purpose:** nginx configuration for the containerized SPA and API proxy.

## Current implementation

Serves `/usr/share/nginx/html`, provides SPA history fallback, proxies `/api/` to `api:8000`, preserves the same-origin session cookie, overwrites `X-Forwarded-For`/`X-Forwarded-Proto`, sets CSP with `frame-ancestors 'none'`, COOP, frame and referrer headers, and serves hashed assets without caching HTML.

## Verification

Static nginx checks pass: balanced braces, `listen 80`, `server_tokens off`, expected root/upstream, API proxy and security headers. The config is copied by `apps/web/Dockerfile`.

## Unresolved issues

No nginx binary or container runtime is available in this workspace, so `nginx -t` and a real container smoke test remain operator/staging work.
