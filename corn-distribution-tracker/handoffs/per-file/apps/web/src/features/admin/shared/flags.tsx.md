# File Handoff: `apps/web/src/features/admin/shared/flags.tsx`

**Status:** IMPLEMENTED  
**Primary owner:** Frontend  
**File purpose:** Shared geo flags UI

## Responsibility
Renders geo indicator statuses/flags consistently across admin tables and cards.

## Contract and dependencies
See the relevant contract under `docs/` and the ownership table in `handoffs/file_map.md`; this file was added during implementation and integrates with the shared API/session/query layers.

## Implementation summary

Shared geo-flag/status rendering for admin surfaces, avoiding duplicated label/tone logic.

**Verification (2026-10-22):** `cd apps/web && npm test` → 14 passed (3 files); `npm run lint` → 0 errors/0 warnings; `npm run build` → tsc + Vite production build succeeded.

**Unresolved issues:** None known.
