# QA Agent Handoff

## Own
Backend tests under `apps/api/tests/**`, web component tests, smoke/E2E tests and release-gate evidence. Add file-level handoffs for any new test/support files.

## Prioritize adversarial and integrity paths
- Direct API access with altered user, assignment, site, evidence and distribution IDs.
- Concurrent allocations/submissions at the exact available-stock boundary.
- Duplicate idempotency keys; response lost after transaction commit; repeated approve.
- Rejection, cancellation, correction/reversal semantics.
- Unit conversions and decimal precision.
- Location capture with missing/stale/inaccurate/far fixes (confirm no warning and no approval gate); absent EXIF; duplicate photo hash; capture-time mismatch; unexpected file type.
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
- 360 px audit: all current routes (login, forgot/reset/invite/change-password modes, 10 admin routes and the distributor routes) had `scrollWidth = 360`, headings clear of the top bar, no horizontal overflow, no unexpected console errors and no 5xx responses. Invitation one-time-link dialog, audit action filter, local draft discard, settings round-trip and drawer scroll lock/Escape/focus restoration were checked separately. The new long sign-in `429` alert was rechecked at 360 px with `scrollWidth = 360`.
- Backup/restore: local Django-schema drill passed (83,441-byte dump; both corn migrations restored; all table counts matched; zero missing evidence objects). Production provider drill remains operator-owned.
- Native local smoke (2026-10-23): Django `runserver` + Vite, `/health/live`, `/health/ready`, login page and session bootstrap verified without a container runtime.

## Current regression evidence (2026-10-25)

- Backend: **66 passed**, Ruff clean, mypy clean in **50 source files**. The configuration test guards the raw evidence-upload ceiling; a 7.0 MB authenticated JPEG upload returned `204`. Campaign-site coverage includes optional setup, generated codes, duplicate names, optional/cleared locations, cross-campaign rejection, campaign-scoped analytics/map filtering and geo evaluation without site coordinates.
- Frontend: **37 passed** across 6 Vitest files; TypeScript and ESLint clean; production build passed. Component tests cover campaign-dialog site names, name-only site add and optional location later.
- Browser E2E: **8 passed** after the campaign-site changes. The suite still seeds its site through the API and attaches it via assignment, so the campaign-site panel itself is covered by component/API tests rather than browser automation.
- Phone/HTTPS: login, assigned sites and delivery flow worked through an HTTPS quick tunnel. A captured fix (`28.613900, 77.209000 ±12.0 m`, mocked browser position) was stored; a resumed draft kept its saved fix and the submission payload preserved it.
- Location policy: the old `GPS_MISSING`/`OUTSIDE_GEOFENCE` demo cases were superseded. The current tests prove that missing, stale, inaccurate and far-away fixes produce no location flags and can be approved manually without an exception. Only duplicate hash, capture-time mismatch and unexpected file type require an override; target overruns still require one. The old Juba records were deleted in the scoped cleanup after backup.


## Location-warning removal and data cleanup (2026-10-25)

- Backend **66 passed**, Ruff clean, mypy clean in 50 source files, migration check no changes. New assertions cover far/stale/inaccurate/missing fixes with `geo_flags == []`, `geo_status` `PASS`/`UNAVAILABLE`, approval without a location exception, EXIF GPS difference stored without a flag, and duplicate-image critical behavior retained.
- Frontend **37 passed** across 6 files, TypeScript/ESLint clean, production build passed, browser E2E **8 passed**.
- Development cleanup verification: one campaign/site/assignment/record/evidence, three accounts/movements, three users, one `Asia/Kolkata` settings row, zero upload intents/invitations, one private storage file. `stock_movements_append_only` and `audit_events_append_only` triggers were confirmed enabled after the cleanup.
- Retained ledger balances are intentionally not zeroed: central 30,000 kg, Amina 19,999 kg, Kolhapur site 1 kg, derived from the retained 50,000 kg receipt, 20,000 kg allocation and 1 kg delivery. The chain exists to back the approved record; no historical movement was rewritten.
- **Open QA gap:** no committed browser assertion that admin review omits location warnings. The component/API tests plus manual review cover the behavior today.

## Delivery-only admin map (2026-10-25)

- Backend coverage added to `test_analytics_scope.py`: `/analytics/map-deliveries` returns only a record with a captured fix (a no-location submission is excluded), checks site/distributor/quantity/coordinate fields, rejects distributor access, applies bbox filtering/validation, still returns the point after approval with status `APPROVED`, and excludes a rejected claim. Current suite: **67 passed**; Ruff/mypy clean in 50 source files; migration check unchanged.
- Frontend coverage added in `DistributionMapPage.test.tsx`: the page renders the delivery list and delivery-only map label, no longer renders “Sites in scope”, opens the selected delivery drawer with the evidence-review link, and shows the no-delivery empty state. Current suite: **39 passed across 7 files**; TypeScript/ESLint clean; production build passed.
- Browser E2E now includes a ninth test: after approval, an admin opens `/map`, sees the approved 25 kg E2E delivery as the delivery point, verifies one `.map-pin`, asserts the drawer shows `4.851000, 31.582000` and an evidence-review link, and confirms no “Sites in scope” heading. Current E2E: **9 passed** (2 setup + 7 workflow).
- The retained development approved Kolhapur record(s) have captured fixes and a name-only site, so they appear as delivery points without adding site coordinates. The map intentionally has no admin-location marker and no site-reference markers.
- A headless Chromium smoke with an authenticated admin session rendered the live `/map` page: two approved Kolhapur records produced two list entries and two map pins, selecting one opened the drawer with coordinates/accuracy, OpenStreetMap/Google Maps links and “Open evidence review”, no “Sites in scope” section appeared, and there were no console errors or non-tile request failures.
- **Not covered:** the E2E asserts markers/list data, not WebGL tile loading or the coordinate-board fallback; no committed test forces MapLibre initialization failure. That is a rendering-fallback gap, not a data or API gap.
