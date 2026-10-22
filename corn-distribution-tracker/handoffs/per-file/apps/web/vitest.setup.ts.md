# File Handoff: `apps/web/vitest.setup.ts`

**Status:** TESTED  
**Primary owner:** Frontend  
**File purpose:** Vitest setup

## Responsibility
Loads jest-dom and polyfills a functional in-memory Storage when Node's webstorage shadows jsdom (Node 25).

## Contract and dependencies
See the relevant contract under `docs/` and the ownership table in `handoffs/file_map.md`; this file was added during implementation and integrates with the shared API/session/query layers.

## Implementation summary

Loads jest-dom matchers and installs an in-memory `Storage` when Node's experimental webstorage shadows jsdom's implementation. Required for the web suite to pass on Node 25.

**Verification (2026-10-22):** `cd apps/web && npm test` → 14 passed (3 files); `npm run lint` → 0 errors/0 warnings; `npm run build` → tsc + Vite production build succeeded.

**Unresolved issues:** None known.
