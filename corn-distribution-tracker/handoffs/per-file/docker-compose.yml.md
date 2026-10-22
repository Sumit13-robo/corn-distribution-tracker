# File Handoff: `docker-compose.yml`

**Status:** IMPLEMENTED  
**Primary owner:** DevOps / Lead Integrator  
**File purpose:** Local stack

## Responsibility
Run web, API, PostgreSQL+PostGIS and optional development object storage; health dependencies, named volumes and explicit dev-only defaults. Never use production credentials.

## Contract and dependencies
env template; Dockerfiles

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- Clean startup, migration and smoke flow documented.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Local stack: PostGIS Postgres with healthcheck, API container (migrations then uvicorn) and nginx-served web with build-time VITE_* args (API base and optional map style; public only). YAML parses cleanly; the unused `VITE_APP_NAME` arg was removed. Not built here (Docker unavailable).

**Verification (2026-10-22):** Parsed with PyYAML (`api`, `db`, `web` services resolved); both Dockerfiles pass hadolint 2.15.1. Backend 46 tests and web 14 tests pass; E2E 7 passed. Docker image/compose execution was **not** run because no Docker/Podman daemon is available.

**Unresolved issues:** Image/compose build was not executed because Docker is unavailable in this environment.
