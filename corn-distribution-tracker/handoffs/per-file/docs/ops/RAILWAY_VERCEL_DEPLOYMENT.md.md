# File Handoff: `docs/ops/RAILWAY_VERCEL_DEPLOYMENT.md`

**Status:** IMPLEMENTED
**Primary owner:** DevOps / Lead Integrator
**File purpose:** Operator guide for the Railway API/Postgres/Bucket and Vercel SPA topology.

## Current implementation

Documents backend and frontend service setup, root directories, environment
variables, bucket CORS and virtual-host settings, first-admin bootstrap,
production checks and known provider boundaries.

## Verification

- Cross-checked against `railway.json`, `vercel.json`, `.env.railway.example`,
  `infra/railway-bucket-cors.json` and the existing deployment runbook.
- No provider deployment was performed from this workspace.

## Unresolved issues

Real provider upload/CORS/KMS, cookie round-trip, TLS and restore evidence remain
operator-owned.
