# File Handoff: `apps/api/bin/start.sh`

**Status:** IMPLEMENTED
**Primary owner:** Backend / DevOps
**File purpose:** PORT-aware Gunicorn startup for local Docker and Railway.

## Current implementation

Starts Gunicorn on `0.0.0.0:${PORT:-8000}` with configurable worker count,
timeout, graceful timeout and max-request recycling. Logs access/errors to
stdout/stderr.

## Verification

- `sh -n apps/api/bin/start.sh` → syntax clean.
- `gunicorn --check-config config.wsgi:application` → passes.
- Full API suite: 98 passed. No live Railway start was performed.

## Unresolved issues

Real provider startup, worker sizing and load behavior remain external.
