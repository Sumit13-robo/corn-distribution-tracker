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

**Verification (2026-10-23):** `cd apps/web && npm test` → 39 passed (7 files); `npm run lint` → 0 errors/0 warnings; `npm run build` → tsc + Vite production build succeeded.

**Unresolved issues:** None known.

## Location display update (2026-10-25)

The distance formatter remains available for optional/legacy context but no delivery, site or review screen renders distance as a warning. Location labels use captured/missing. Verification: `npm test` → 39 passed; typecheck/lint/build pass.
