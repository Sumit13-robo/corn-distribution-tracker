# File Handoff: `apps/api/tests/test_config_security.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Production/staging configuration fail-fast tests

## Current implementation

Production/staging configuration fail-fast tests, plus a check that the raw upload memory ceiling is larger than the configured evidence cap. It now also covers the Railway public-host and bucket fallback names, the single `FRONTEND_ORIGIN` path, and rejection of a non-HTTPS production frontend origin.

## Verification

Backend: `make test-api` → 98 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 51 source files; migration check → no changes. The new `test_raw_upload_limit_covers_configured_evidence_cap` guards the 7 MB phone-photo regression.

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.
