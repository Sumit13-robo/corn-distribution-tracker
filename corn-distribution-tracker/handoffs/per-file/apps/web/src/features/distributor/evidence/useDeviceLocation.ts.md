# File Handoff: `apps/web/src/features/distributor/evidence/useDeviceLocation.ts`

**Status:** TESTED
**Primary owner:** Frontend
**File purpose:** Geolocation hook

## Responsibility
Wrap browser geolocation with permission/loading/error/timeout/staleness states; return accuracy and timestamp; request only after action.

## Contract and dependencies
geo evidence spec

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- Mocked browser API tests for success/denial/timeout/stale.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Geolocation request capturing coordinates, accuracy and fix timestamp with explicit failure states; returns a snapshot for the submission payload or null. Coordinates are rounded to six decimal places before display/draft persistence to match the API/serializer and PostgreSQL schema (previously seven places caused a server-side 422). The hook checks `window.isSecureContext === false` before calling the API and returns a specific HTTPS-required message; this prevents a misleading permission-denied message on HTTP LAN development URLs. Real-browser HTTPS capture was verified with a mocked Delhi fix.

**Verification (2026-10-25):** `cd apps/web && npm test` → 34 passed (5 files), including the six-decimal persistence test and the insecure-origin guidance test; `npx tsc -b --noEmit` and `npx eslint src --max-warnings=0` passed; `npm run build` passed. An HTTPS quick-tunnel smoke captured `28.613900, 77.209000 ±12.0 m` with no permission error.

**Unresolved issues:** Browser geolocation still depends on a secure context and OS-level location permission. An HTTP LAN URL is not sufficient, regardless of the site permission setting.

## Location policy update (2026-10-25)

The hook still returns accuracy/timestamp and distinguishes denial, timeout, insecure origin and unsupported states, but no caller treats those states as approval blockers or location warnings. Capture remains optional. Verification: `npm test` → 37 passed; typecheck/lint/build pass.
