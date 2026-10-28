# File Handoff: `docker-compose.yml`

**Status:** IMPLEMENTED
**Primary owner:** DevOps/Lead
**File purpose:** Optional container stack with database/API/web health dependencies and storage-aware readiness.

## Current implementation

The Compose stack defines PostgreSQL, the Django/Gunicorn API and the nginx-served SPA. The API uses a readiness healthcheck (not only liveness), and nginx uses the `api:8000` upstream. The documented local workflow still runs native PostgreSQL, Django and Vite.

## Verification

YAML parsed locally; service dependencies and healthchecks asserted; nginx/Dockerfile static checks pass. The native path, 98 API tests, 39 web tests, production build and 9 Playwright tests are verified. Container startup is not exercised in this workspace.

## Unresolved issues

Container runtime verification is deferred because no Docker/Podman/Buildah is available.
