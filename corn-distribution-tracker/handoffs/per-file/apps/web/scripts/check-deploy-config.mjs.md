# File Handoff: `apps/web/scripts/check-deploy-config.mjs`

**Status:** IMPLEMENTED
**Primary owner:** Frontend / DevOps
**File purpose:** Fail a Vercel build when the API proxy placeholder has not been replaced.

## Current implementation

Reads `apps/web/vercel.json`; when running under Vercel and the Railway
placeholder host is still present, prints an actionable error and exits 1.
Local builds are unaffected.

## Verification

- Executed locally with no `VERCEL` variable: exits 0.
- The Vercel failure path is a guarded build check; no provider deployment was
  performed.

## Unresolved issues

The check intentionally targets the documented placeholder string only.
