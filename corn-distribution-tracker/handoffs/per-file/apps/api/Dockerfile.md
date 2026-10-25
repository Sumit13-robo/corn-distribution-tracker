# File Handoff: `apps/api/Dockerfile`

**Status:** DEFERRED
**Primary owner:** Backend / DevOps
**File purpose:** Optional API container definition (not part of the supported native workflow).

## Current implementation

Gunicorn API container definition retained in the repository. The documented local workflow runs Django directly against native PostgreSQL; container startup is not exercised or claimed as verified.

## Verification

Native path verified separately: `make test-api` → 66 passed; Ruff and mypy clean; migration check no changes; Playwright E2E 8 passed.

## Unresolved issues

Container build/runtime is deferred and outside the supported native workflow.
