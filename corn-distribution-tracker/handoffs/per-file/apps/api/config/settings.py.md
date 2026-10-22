# File Handoff: `apps/api/config/settings.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Environment-driven Django settings, structured logging and fail-fast production validation

## Current implementation

Environment-driven Django settings, structured logging and fail-fast production validation. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 58 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 49 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (8 passed).

## Unresolved issues

None known. Docker image build/runtime remains unverified on this host (no Docker daemon).
