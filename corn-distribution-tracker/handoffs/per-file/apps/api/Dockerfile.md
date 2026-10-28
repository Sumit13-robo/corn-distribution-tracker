# File Handoff: `apps/api/Dockerfile`

**Status:** IMPLEMENTED
**Primary owner:** Backend / DevOps
**File purpose:** API container definition with non-root runtime, pinned base image and readiness-aware healthcheck.

## Current implementation

Gunicorn API container definition. The Dockerfile copies the API dependencies/application, runs as UID/GID `10001`, and healthchecks readiness through Gunicorn. The documented local workflow still runs Django directly against native PostgreSQL; container startup is not exercised in this workspace.

## Verification

`gunicorn --check-config config.wsgi:application` passes from `apps/api`. Static Dockerfile checks pass (pinned base image, non-root user, healthcheck, no mutable `latest` tag). Native path: `make test-api` → 98 passed; Ruff and mypy clean; migration check no changes; Playwright E2E 9 passed.

## Unresolved issues

Container build/runtime is deferred; no Docker/Podman/Buildah is available in this workspace.

## 2026-10-28 Railway packaging

The image now copies the executable `bin/` scripts, uses a `PORT`-aware runtime
healthcheck, and starts through `bin/start.sh` (Gunicorn binds
`0.0.0.0:${PORT:-8000}`). `bin/release.sh` is reserved for Railway's
`preDeployCommand`. `PORT` defaults to `8000` for local Docker/Compose.

Verification: `sh -n` on both scripts, `gunicorn --check-config`, and the API
suite (98 passed). The image itself was not built because no Docker runtime is
available.
