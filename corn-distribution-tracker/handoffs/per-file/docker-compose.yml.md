# File Handoff: `docker-compose.yml`

**Status:** IMPLEMENTED
**Primary owner:** DevOps/Lead
**File purpose:** Local PostgreSQL, Django/Gunicorn API and nginx SPA stack.

## Current implementation

PostgreSQL 17 (no PostGIS extension), API image with Django migrations before Gunicorn, private evidence volume, health-gated dependencies, and same-origin nginx proxy. Vite build arguments are public only. Development credentials are explicit local defaults; production must use a managed database, S3 storage and secure secret/cookie settings.

## Verification

YAML/config reviewed. **Docker/Compose startup was not executed** on this host because Docker/Podman/Buildah and rootless namespaces are unavailable. The non-Docker local path, tests, build and Playwright are verified.

## Unresolved issues

Image build, health-gated startup and nginx cookie/proxy behavior remain unverified until run on a Docker-capable host.
