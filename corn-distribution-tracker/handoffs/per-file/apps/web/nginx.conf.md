# File Handoff: `apps/web/nginx.conf`

**Status:** IMPLEMENTED  
**Primary owner:** DevOps/Lead  
**File purpose:** Web container server

## Responsibility
SPA history fallback, cache/security headers and same-origin `/api/` proxy to `api:8000`.

## Contract and dependencies
See the relevant contract under `docs/` and the ownership table in `handoffs/file_map.md`; this file was added during implementation and integrates with the shared API/session/query layers.

## Implementation summary

SPA server with history fallback, static asset caching, security headers and a same-origin `/api/` proxy to `api:8000` (keeps the refresh cookie first-party). Not executed here (Docker unavailable).

**Verification (2026-10-22):** `cd apps/web && npm test` → 14 passed (3 files); `npm run lint` → 0 errors/0 warnings; `npm run build` → tsc + Vite production build succeeded.

**Unresolved issues:** Image/compose build was not executed because Docker is unavailable in this environment.
