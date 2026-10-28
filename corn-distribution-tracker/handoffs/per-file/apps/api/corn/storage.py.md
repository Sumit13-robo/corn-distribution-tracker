# File Handoff: `apps/api/corn/storage.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Private local/S3 evidence storage and short-lived signed URLs

## Current implementation

Private local/S3 evidence storage and short-lived signed URLs. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`.

## Verification

Backend: `make test-api` → 98 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 51 source files; migration check → no changes. Wire-level behavior is covered by the Playwright E2E suite (9 passed).

## Unresolved issues

None known. Native PostgreSQL + Django + Vite workflow verified.

## 2026-10-26 audit remediation

S3 now supports health/stat/presigned PUT/upload headers and bounded reads; local storage returns at most `max_bytes + 1` and writes atomically with restrictive permissions. SSE/KMS headers are returned to the browser.

Verification for the current tree: 98 API tests, 39 web tests, 9 Playwright E2E tests, Ruff/mypy/migration/build gates clean. External provider/container/proxy evidence remains operator-owned.

## 2026-10-28 Railway Buckets

Boto3 clients now honor `STORAGE_ADDRESSING_STYLE`. This is required because
boto3 defaults to path-style URLs for a custom endpoint, while Railway Buckets
use virtual-hosted URLs (`<bucket>.t3.storageapi.dev`). `auto` keeps provider
defaults; `virtual` and `path` are explicit production settings.

Verification: `make test-api` → 98 passed, including a presigned-URL host
assertion for `virtual`; Ruff/mypy clean. A real bucket upload/CORS exercise
remains external.
