# File Handoff: `apps/web/eslint.config.js`

**Status:** TESTED
**Primary owner:** DevOps/Lead
**File purpose:** ESLint flat config

## Responsibility
ESLint 9 + typescript-eslint + react-hooks flat config with test overrides; lint runs with zero warnings.

## Contract and dependencies
See the relevant contract under `docs/` and the ownership table in `handoffs/file_map.md`; this file was added during implementation and integrates with the shared API/session/query layers.

## Implementation summary

ESLint 9 flat config: JS/TypeScript recommended + react-hooks rules, test-file overrides. `eslint src --max-warnings=0` passes.

**Verification (2026-10-22):** `cd apps/web && npm test` → 18 passed (3 files); `npm run lint` → 0 errors/0 warnings; `npm run build` → tsc + Vite production build succeeded.

**Unresolved issues:** None known.
