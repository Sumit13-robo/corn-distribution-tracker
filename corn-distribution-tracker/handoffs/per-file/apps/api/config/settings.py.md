# File Handoff: `apps/api/config/settings.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Environment-driven Django settings, structured logging and fail-fast production validation

## Current implementation

Environment-driven Django settings, structured logging and fail-fast production validation. It participates in the Django/DRF request → serializer → service → ORM flow and preserves the contracts in `docs/architecture/API_CONTRACT.md` and the security rules in `docs/architecture/SECURITY_AND_PRIVACY.md`. `DATA_UPLOAD_MAX_MEMORY_SIZE` is derived from `MAX_EVIDENCE_UPLOAD_BYTES + 1 MiB` so the raw evidence PUT endpoint can accept phone photos up to the configured evidence cap; the service still validates the cap, type, magic bytes and image decoding.

## Verification

Backend: `make test-api` → 98 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 51 source files; migration check → no changes. A 7.0 MB JPEG upload through the authenticated HTTPS endpoint returned `204`, and a settings test asserts the raw-body ceiling remains above the evidence cap.

## Unresolved issues

None known. Production still needs a trusted HTTPS origin for real phone geolocation and appropriate reverse-proxy body limits.

## 2026-10-26 audit remediation

Added Django XFrameOptionsMiddleware alongside the custom security headers, explicit trusted-proxy handling for X-Forwarded-For, storage-aware readiness configuration and production fail-fast settings. HSTS/TLS policy still belongs to the ingress owner.

Verification for the current tree: 98 API tests, 39 web tests, 9 Playwright E2E tests, Ruff/mypy/migration/build gates clean. External provider/container/proxy evidence remains operator-owned.

## 2026-10-28 Railway/Vercel deployment

Added Railway public/private hostname auto-allowlisting (plus
`healthcheck.railway.app` for Railway's probe), a single `FRONTEND_ORIGIN`
input that is appended to CORS and CSRF, Railway Bucket variable fallbacks
(`ENDPOINT`, `REGION`, `BUCKET`, `ACCESS_KEY_ID`, `SECRET_ACCESS_KEY`), and
validated `STORAGE_ADDRESSING_STYLE` (`auto|path|virtual`). Production rejects a
non-HTTPS `FRONTEND_ORIGIN`. `TRUST_X_FORWARDED_FOR` remains opt-in.

Verification: `make test-api` → 98 passed (including Railway host/bucket
fallback and virtual-host storage tests); Ruff and mypy clean. Real provider
configuration remains external.
