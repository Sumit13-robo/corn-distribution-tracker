# File Handoff: `apps/api/corn/services/evidence.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Upload intents, image validation, evidence persistence and private view authorization

## Current implementation

Upload intents, image validation, evidence persistence and private view authorization. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 66 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 50 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (8 passed).

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.

## Location policy update (2026-10-25)

The service still validates bytes/type/dimensions, calculates SHA-256, reads EXIF when available and stores EXIF GPS/time plus any EXIF-vs-reported distance as metadata. It no longer emits `GPS_*` or `EXIF_GPS_MISMATCH`; only duplicate hash, capture-time mismatch and unexpected file type are integrity flags. Private storage/originals and signed URL authorization are unchanged. Verification: `make test-api` → 66 passed; mapper/upload tests retained.
