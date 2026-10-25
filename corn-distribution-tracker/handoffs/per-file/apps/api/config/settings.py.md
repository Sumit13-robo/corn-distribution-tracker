# File Handoff: `apps/api/config/settings.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Environment-driven Django settings, structured logging and fail-fast production validation

## Current implementation

Environment-driven Django settings, structured logging and fail-fast production validation. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`. `DATA_UPLOAD_MAX_MEMORY_SIZE` is derived from `MAX_EVIDENCE_UPLOAD_BYTES + 1 MiB` so the raw evidence PUT endpoint can accept phone photos up to the configured evidence cap; the service still validates the cap, type, magic bytes and image decoding.

## Verification

Backend: `make test-api` → 66 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 50 source files; migration check → no changes. A 7.0 MB JPEG upload through the authenticated HTTPS endpoint returned `204`, and a settings test asserts the raw-body ceiling remains above the evidence cap.

## Unresolved issues

None known. Production still needs a trusted HTTPS origin for real phone geolocation and appropriate reverse-proxy body limits.
