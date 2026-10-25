# File Handoff: `apps/web/nginx.conf`

**Status:** IMPLEMENTED
**Primary owner:** DevOps/Lead
**File purpose:** SPA server with same-origin API proxy.

## Current implementation

Serves the built SPA with history fallback, caches hashed assets, adds security headers, and proxies `/api/` to a native Django/Gunicorn upstream at `127.0.0.1:8000` (adjust the upstream/root for the deployment). Same-origin API calls keep the Django `sessionid` cookie first-party; no refresh-token cookie or bearer header is involved. `/api/v1/auth/csrf` supports explicit CSRF bootstrap when needed.

## Verification

Static configuration review only; reverse-proxy runtime was not exercised. Native Django + Vite path verified.

## Unresolved issues

Reverse-proxy runtime remains deployment-specific.
