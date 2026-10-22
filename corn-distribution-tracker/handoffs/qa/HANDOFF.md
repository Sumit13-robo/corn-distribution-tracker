# QA Agent Handoff

## Own
Backend tests under `apps/api/tests/**`, web component tests, smoke/E2E tests and release-gate evidence. Add file-level handoffs for any new test/support files.

## Prioritize adversarial and integrity paths
- Direct API access with altered user, assignment, site, evidence and distribution IDs.
- Concurrent allocations/submissions at the exact available-stock boundary.
- Duplicate idempotency keys; response lost after transaction commit; repeated approve.
- Rejection, cancellation, correction/reversal semantics.
- Unit conversions and decimal precision.
- GPS edge conditions, stale timestamp, excessive reported accuracy, outside-radius point, absent EXIF and duplicate photo hash.
- Signed URL expiry/authorization and upload-size/type limits.
- Filtered analytics and CSV formula injection.
- Offline queue/user switch/session expiry/retry conflict.
- Loading/empty/error states, mobile layout, keyboard focus, permissions and reduced motion.

## Rules
- Use synthetic factories and isolated test storage; never real farm photos/user details.
- Tests must verify database outcomes, not just response codes.
- Make race-condition tests deterministic where possible and repeat them as a stress/smoke test.
- Report flaky tests honestly and never weaken authorization tests to get a green build.
