# File Handoff: `apps/api/tests/test_config_security.py`

**Status:** TESTED  
**Primary owner:** Backend  
**File purpose:** Configuration fail-fast tests

## Responsibility
Prove that production/staging refuse insecure configuration (placeholder secret, insecure cookies, local evidence
storage, wildcard CORS with credentials) while development/test may keep the documented sample defaults. Settings are
constructed with synthetic values and `_env_file=None` so a local `.env` cannot change the result.

## Contract and dependencies
`app/core/config.py`; deployment runbook; security/privacy contract.

## Implementation summary

Adds four tests: production rejects placeholder defaults (validation list + `RuntimeError` on startup),
hardened production settings pass, staging rejects the sample secret, and development remains convenient.
`get_settings()` now fails startup via `assert_secure_settings()` instead of only logging.

**Verification (2026-10-22):** `make test-api` → 46 passed; `make lint-api` → clean; `make typecheck-api` → clean.

**Unresolved issues:** None known.
