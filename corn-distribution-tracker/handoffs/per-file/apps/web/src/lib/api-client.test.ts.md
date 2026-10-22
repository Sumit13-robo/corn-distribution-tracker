# File Handoff: `apps/web/src/lib/api-client.test.ts`

**Status:** TESTED  
**Primary owner:** Frontend  
**File purpose:** API client tests

## Responsibility
Covers single-flight refresh, rotated-token retry, failed-refresh auth loss, token-less requests and error envelope mapping (4 tests).

## Contract and dependencies
See the relevant contract under `docs/` and the ownership table in `handoffs/file_map.md`; this file was added during implementation and integrates with the shared API/session/query layers.

## Implementation summary

Covers single-flight refresh, rotated-token retry, failed-refresh auth loss, token-less requests and error envelope mapping (4 tests).

**Verification (2026-10-22):** `cd apps/web && npm test` → 13 passed (3 files); `npm run lint` → 0 errors/0 warnings; `npm run build` → tsc + Vite production build succeeded.

**Unresolved issues:** None known.
