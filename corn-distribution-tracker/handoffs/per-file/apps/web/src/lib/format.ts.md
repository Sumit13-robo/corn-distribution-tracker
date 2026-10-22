# File Handoff: `apps/web/src/lib/format.ts`

**Status:** IMPLEMENTED
**Primary owner:** Frontend
**File purpose:** Shared formatting helpers

## Responsibility
kg/number/date/relative-age/distance/bytes formatters plus `humanizeStatus` and `cx`; used across screens.

## Contract and dependencies
See the relevant contract under `docs/` and the ownership table in `handoffs/file_map.md`; this file was added during implementation and integrates with the shared API/session/query layers.

## Implementation summary

Shared formatting helpers for kg/numbers, dates/times, relative age, distances, bytes, class names and enum status labels; used across screens and tested indirectly.

**Verification (2026-10-22):** `cd apps/web && npm test` → 18 passed (3 files); `npm run lint` → 0 errors/0 warnings; `npm run build` → tsc + Vite production build succeeded.

**Unresolved issues:** None known.
