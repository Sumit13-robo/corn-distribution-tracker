# File Handoff: `apps/web/src/features/distributor/deliveries/DeliverySubmissionPage.tsx`

**Status:** TESTED
**Primary owner:** Frontend
**File purpose:** Delivery form workflow

## Responsibility
Guide location → photo → quantity/unit → review → submit, persist draft/idempotency key, display warnings, handle online/offline/conflict/error and confirm only server-accepted submissions.

## Contract and dependencies
evidence capture; API client; queue

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- No duplicate submission; offline/local state clear.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Draft auto-save with persistent idempotency key and resume-on-return, evidence capture, immediate persistence of a captured device fix into the draft (so the UI reflects it and reloads do not lose it), unit conversion preview/warnings, duplicate-submit guard, online sync vs honest QUEUED and success only after a server record id. Location display and warnings read the fresh fix or the fix saved with the draft, so a resumed draft does not falsely say “Location not captured”; submitting without a fresh fix preserves the saved draft fix instead of clearing it. The location copy now says capture is optional context and never blocks approval; no distance/geofence check is shown.

**Verification (2026-10-25):** `cd apps/web && npm test` → 34 passed (5 files, including the saved-fix remount/submission test); `npx tsc -b --noEmit` and `npx eslint src --max-warnings=0` passed; `npm run build` succeeded. Browser smoke confirmed the captured coordinates survived a reload and the review warning disappeared.

**Final verification (2026-10-25):** `npm test` → 37 passed across 6 files; `npm run typecheck`, `npm run lint`, `npm run build` (app JS 520.67 kB gzip 156.03 kB) and `make test-e2e` (8 passed) all pass. The copy-only change does not alter submission behavior.

**Unresolved issues:** Browsers still require a secure HTTPS origin and OS location permission. No location warning blocks approval, and name-only sites have no distance display.

## Location-warning removal (2026-10-25)

The form no longer shows distance, geofence/GPS-quality warnings or a “too far” advisory. It shows the captured/missing state plus coordinates/accuracy when present; a denied permission still allows submission. The saved-draft fix behavior is preserved. Verification: `npm test` → 37 passed across 6 files; typecheck/lint/build and `make test-e2e` (8 passed) pass.
