# File Handoff: `README.md`

**Status:** IMPLEMENTED
**Primary owner:** DevOps / Lead Integrator
**File purpose:** Repository run guide

## Responsibility
Explain architecture, prerequisites, native setup, env, migration, first admin bootstrap, tests, run commands, evidence storage setup, deployment and known limits. State what is actually implemented.

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

Native run guide covering architecture, PostgreSQL/Django/Vite setup, health checks, first-admin bootstrap, tests, browser E2E, configuration and an honest limitations list. The documented workflow does not require a container runtime. The map section documents OpenStreetMap street + Esri satellite basemaps, Google Maps link-outs and provider-licensing limits.

**Verification (2026-10-25):** The map/location update was re-verified with web typecheck, ESLint, 34 Vitest tests (9 map tests), a production build and a headless Chromium smoke (OSM + Esri tiles, satellite switch, mocked New Delhi locate, Google Maps links). Current backend count is 61 tests; E2E 8 and native smoke remain recorded in the dated verification table.

**Unresolved issues:** Public OSM/Esri tiles are not production-scale providers; Google Maps embedding still requires a key and billing.

**Unresolved issues:** None known for the documented native path. Deferred product features are listed in the README.
