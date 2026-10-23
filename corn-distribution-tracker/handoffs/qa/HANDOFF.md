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

## Release-gate evidence (2026-10-23)

- Backend: **60 passed**, Ruff clean, mypy clean in 49 source files, Django migration check clean. New coverage: successful sign-ins do not consume the per-IP failure window; ten failures still return `429`; a locked account reports its remaining retry window.
- Frontend unit/component: **23 passed** across 4 Vitest files; ESLint 0 warnings; `tsc -b` clean; production build succeeded. New coverage: generic credential errors, rate-limit retry messaging, and network/5xx sign-in failures.
- Browser E2E: **8 passed** (2 API-seeded setup + 6 workflow) against real Django/DRF + PostgreSQL + Chromium (rerun 2026-10-23 after the login-throttle change). The suite uses a disposable database, per-run generated credentials and only synthetic data; `run-e2e.mjs` prepares the database before Playwright web servers start.
- 360 px audit: all **20 screens** (login, forgot/reset/invite/change-password modes, 10 admin routes and 5 distributor routes) had `scrollWidth = 360`, headings clear of the top bar, no horizontal overflow, no unexpected console errors and no 5xx responses. Invitation one-time-link dialog, audit action filter, local draft discard, settings round-trip and drawer scroll lock/Escape/focus restoration were checked separately. The new long sign-in `429` alert was rechecked at 360 px with `scrollWidth = 360`.
- Backup/restore: local Django-schema drill passed (83,441-byte dump; both corn migrations restored; all table counts matched; zero missing evidence objects). Production provider drill remains operator-owned.
- Docker: images/compose **not executed** (no Docker/Podman daemon on this host); treat runtime verification as pending on a Docker-capable host.
