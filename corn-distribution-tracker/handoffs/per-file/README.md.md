# File Handoff: `README.md`

**Status:** IMPLEMENTED  
**Primary owner:** DevOps / Lead Integrator  
**File purpose:** Repository run guide

## Responsibility
Explain architecture, prerequisites, setup, env, migration, first admin bootstrap, tests, run commands, evidence storage setup, deployment and known limits. State what is actually implemented.

## Contract and dependencies
all docs

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- A developer can reproduce a clean local install.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Run guide covering architecture, Docker and local workflows, verified command results, browser E2E instructions (including the destructive isolated database warning), invitation-token delivery caveat, configuration and honest limitations.

**Verification (2026-10-22):** Backend 46 tests passed (ruff/mypy clean); web 14 tests passed (lint/build clean); Playwright E2E 8 passed; `npm audit` clean; Docker image build not executed (no daemon); hadolint clean on both Dockerfiles.

**Unresolved issues:** None known.
