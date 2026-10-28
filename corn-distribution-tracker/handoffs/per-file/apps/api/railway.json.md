# File Handoff: `apps/api/railway.json`

**Status:** IMPLEMENTED
**Primary owner:** Backend / DevOps
**File purpose:** Railway service build/deploy policy for the Dockerized API.

## Current implementation

Railway uses the API `Dockerfile`, runs `sh bin/release.sh` as a pre-deploy
migration, starts `sh bin/start.sh`, and gates traffic on `/health/ready`.
Restart-on-failure is bounded to five retries.

## Verification

- `python3 -m json.tool apps/api/railway.json` → valid JSON.
- API suite: `make test-api` → 98 passed.
- Real Railway build, pre-deploy migration and healthcheck are not exercised in
  this workspace.

## Unresolved issues

Provider-side deployment remains operator-owned.
