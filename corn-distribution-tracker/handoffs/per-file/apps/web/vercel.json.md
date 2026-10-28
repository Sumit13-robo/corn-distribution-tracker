# File Handoff: `apps/web/vercel.json`

**Status:** IMPLEMENTED
**Primary owner:** Frontend / DevOps
**File purpose:** Vercel Vite build, same-origin API proxy, SPA fallback and security headers.

## Current implementation

Builds the Vite app, rewrites `/api/:path*` to the Railway API, keeps API
responses uncached, falls back to `index.html` for SPA routes and applies the
CSP/HSTS/frame/referrer/Permissions-Policy headers used by the nginx sample.
The `buildCommand` refuses to build on Vercel while the Railway placeholder
origin is still present.

## Verification

- `python3 -m json.tool apps/web/vercel.json` → valid JSON.
- `npm run build` → passes from `apps/web`.
- Vercel CLI build was not run because the CLI has no valid token in this
  workspace. Replace `your-service.up.railway.app` before deploying.

## Unresolved issues

Real Vercel routing/cookie round-trip and provider deployment remain external.
