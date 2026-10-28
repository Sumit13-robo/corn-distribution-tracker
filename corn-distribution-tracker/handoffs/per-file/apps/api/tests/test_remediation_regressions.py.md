# File Handoff: `apps/api/tests/test_remediation_regressions.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Regression coverage for the 2026-10 audit findings across inventory, distribution, evidence and operations controls.

## Current implementation

Synthetic-data integration tests cover:

- idempotency scope separation and payload conflicts;
- legacy fingerprint-less ledger/delivery keys failing closed;
- reversal integrity, nested/overdraw refusal, receipt reversal reconciliation;
- target-approval locking and unvisited/completed assignment targets;
- campaign/assignment/site-stock scope leaks and distributor-hidden notes;
- `LOSS`/`RETURN` adjustments respecting pending reservations;
- direct-S3 completion, same-size and oversized evidence replacement rejection;
- X-Forwarded-For trust opt-in and bounded rate-limiter storage;
- raced first-site stock-account creation;
- Railway Bucket virtual-host addressing with a custom S3 endpoint.

## Verification

`make test-api` → 98 passed. This file contributes 29 tests and passed independently before the final full run. Ruff/mypy clean.

## Unresolved issues

These are application-level tests. Real provider S3/CORS, proxy/TLS, multi-worker rate limiting and load behavior remain external evidence.
