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

## Release-gate evidence (2026-10-22)

- Backend: **46 passed** (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`), Ruff clean, mypy clean in 65 files.
- Frontend unit/component: **14 passed** across 3 Vitest files; ESLint 0 warnings; `tsc -b` clean; production build succeeded.
- Browser E2E: **8 passed** (2 API-seeded setup + 6 workflow) against real FastAPI + PostgreSQL + Chromium. See `apps/web/playwright.config.ts` and `e2e/distribution.spec.ts`; the suite uses a disposable database, per-run generated credentials and only synthetic data.
- E2E regression finds: distributor assignment nested-site contract (500), captured location not persisted until submit, and horizontal overflow at 360 px. All three are fixed with backend/component/browser regression coverage.
- Backup/restore: local synthetic PostgreSQL dump/restore drill passed (Alembic revision, row counts and evidence objects matched); production provider drill remains operator-owned. See `docs/ops/BACKUP_RESTORE.md`.
- Docker: images/compose **not executed** (no Docker/Podman daemon on this host). Dockerfiles pass hadolint 2.15.1 and compose parses; treat runtime verification as pending on a Docker-capable host.
