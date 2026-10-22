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

Draft auto-save with persistent idempotency key and resume-on-return, evidence capture, immediate persistence of a captured device fix into the draft (so the UI reflects it and reloads do not lose it), unit conversion preview/warnings, duplicate-submit guard, online sync vs honest QUEUED and success only after a server record id.

**Verification (2026-10-22):** `cd apps/web && npm test` → 14 passed (3 files, including the new location-persistence test); `npm run lint` → 0 errors/0 warnings; `npm run build` → tsc + Vite production build succeeded; browser E2E submitted 25 kg with photo/location and approved it.

**Unresolved issues:** None known.
