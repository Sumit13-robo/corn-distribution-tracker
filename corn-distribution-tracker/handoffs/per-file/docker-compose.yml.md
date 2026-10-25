# File Handoff: `docker-compose.yml`

**Status:** DEFERRED
**Primary owner:** DevOps/Lead
**File purpose:** Optional container stack (not part of the supported native workflow).

## Current implementation

The file remains in the repository as an optional container definition. It is not used by the documented local setup; local development runs native PostgreSQL, Django and Vite.

## Verification

The native path, tests, build and Playwright are verified. Container startup is outside the supported workflow and is not claimed as verified.

## Unresolved issues

Container runtime verification is deferred. The committed `apps/web/nginx.conf` now targets a native same-host upstream; adjust it if the compose stack is revived.
