# File Handoff: `Makefile`

**Status:** TESTED
**Primary owner:** DevOps / Lead Integrator
**File purpose:** Developer commands

## Responsibility
Provide predictable commands for native local startup, install, lint, types, tests, migration and admin bootstrap. Commands must not reset production data.

## Contract and dependencies
package/pyproject

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- Every target works as documented.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Developer targets for venv/install/migrations/admin bootstrap/tests/lint/typecheck/build/run, plus `e2e-install` (Chromium), `test-e2e` (real API + disposable PostgreSQL) and `health` (live/readiness probes). `test-api` disables third-party pytest autoload (ROS plugins on this workstation). Container-only `db-up`/`dev-up` targets were removed.

**Verification (2026-10-26):** Backend 98 tests passed (Ruff/mypy clean); web 39 tests passed (lint/build clean); `make test-e2e` 9 passed; native `make health` returned both probes; `npm audit` 0 vulnerabilities.

**Unresolved issues:** None known.

## 2026-10-26 audit remediation

Added the aggregate `make check` target (API/web lint, type checks, migration drift, API/web tests and production web build) as the local counterpart of CI.

Verification for the current tree: 98 API tests, 39 web tests, 9 Playwright E2E tests, Ruff/mypy/migration/build gates clean. External provider/container/proxy evidence remains operator-owned.
