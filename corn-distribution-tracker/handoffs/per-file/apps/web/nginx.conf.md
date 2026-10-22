# File Handoff: `apps/web/nginx.conf`

**Status:** IMPLEMENTED
**Primary owner:** DevOps/Lead
**File purpose:** SPA server with same-origin API proxy.

## Current implementation

Serves the built SPA with history fallback, caches hashed assets, adds security headers, and proxies `/api/` to `api:8000`. Same-origin API calls keep the Django `sessionid` cookie first-party; no refresh-token cookie or bearer header is involved. `/api/v1/auth/csrf` supports explicit CSRF bootstrap when needed.

## Verification

Static configuration review only; Docker/nginx runtime was not executed on this host (no Docker daemon).

## Unresolved issues

Runtime proxy/cookie behavior must be checked on a Docker-capable host.
