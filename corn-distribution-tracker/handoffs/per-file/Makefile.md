# File Handoff: `Makefile`

**Status:** TESTED  
**Primary owner:** DevOps / Lead Integrator  
**File purpose:** Developer commands

## Responsibility
Provide predictable commands for local startup, install, lint, types, tests, migration, seed synthetic dev data and cleanup. Commands must not reset production data.

## Contract and dependencies
package/pyproject/compose

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

Developer targets for venv/install/migrations/admin bootstrap/tests/lint/typecheck/build/run. `test-api` disables third-party pytest autoload (ROS plugins on this workstation); commands verified.

**Verification (2026-10-22):** Backend 45 tests passed (ruff/mypy clean); web 13 tests passed (lint/build clean); Makefile targets exercised. Docker images were **not built** because no Docker daemon was available.

**Unresolved issues:** None known.
