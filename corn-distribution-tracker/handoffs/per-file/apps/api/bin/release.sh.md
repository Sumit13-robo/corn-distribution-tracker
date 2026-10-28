# File Handoff: `apps/api/bin/release.sh`

**Status:** IMPLEMENTED
**Primary owner:** Backend / DevOps
**File purpose:** One-shot pre-deploy Django migration command.

## Current implementation

Runs `python manage.py migrate --noinput` once in Railway's pre-deploy phase so
Gunicorn replicas do not race migrations.

## Verification

- `sh -n apps/api/bin/release.sh` → syntax clean.
- Migration checks pass locally; the full API suite is 98 passed.
- The Railway pre-deploy hook has not been executed from this workspace.

## Unresolved issues

Provider-side migration execution and rollback remain operator-owned.
