# Implementation Decision Log

Record date, decision, alternatives considered, reason, effect on data/API, security impact, tests/docs updated and migration/backward-compatibility impact. Do not silently make a decision that changes stock meaning, user scope, evidence policy or status semantics.

## Decisions preset by this pack
1. Canonical inventory unit is kg, stored as decimal numeric. Display conversions are explicit.
2. Approved delivery is the point at which a distributor-to-site stock movement posts.
3. Submitted records reserve stock but do not count as verified delivery until approved.
4. Ledger movements and audit events are append-only; corrections use compensating movements.
5. Original photos are private; evidence viewing uses short-lived signed URLs.
6. Geolocation and image metadata are indicators subject to spoofing/inaccuracy, not guaranteed proof.
7. Admin first-user bootstrap is a controlled one-time operation, not public signup.
8. Initial product is single-organization; future tenant support requires explicit query-level isolation and tests.

## Implementation decisions (2026-10-22)

1. **Access tokens live in memory only; refresh uses an HttpOnly cookie.**
   Alternative: localStorage/sessionStorage token persistence. Reason: XSS token theft resistance and contract alignment.
   Effect: reload restores the session via `POST /auth/refresh`; API client retries a 401 once after a single-flight refresh.
   Security: no browser-readable refresh token; access token never written to storage. No schema change.

2. **Offline drafts are user-scoped and resume by assignment.**
   Drafts use `corn-tracker:drafts:v1:{userId}` with the idempotency key generated once at draft creation and never
   regenerated on retry. Reopening the submission screen resumes the existing `LOCAL_DRAFT`/`QUEUED` draft for that
   assignment instead of creating a second one. Alternative: one draft per screen visit (rejected: duplicate keys and
   stranded data). No schema change; aligns with `OFFLINE_SYNC.md`.

3. **Honest offline labeling.** `LOCAL_DRAFT → QUEUED → UPLOADING → SUBMITTED`; only a server record id moves a draft
   to `SUBMITTED`. Failed syncs return to `QUEUED` with the error. No optimistic “submitted” state.

4. **Evidence upload intent flow.** The client requests an intent, uploads the blob (bearer only for relative API URLs,
   intent headers for presigned URLs), then submits the record with evidence intent ids. Types are restricted to
   JPEG/PNG/WebP with a 10 MB cap, content is sniffed server-side, SHA-256 hashed, and stored privately. Viewing uses
   short-lived signed URLs. Alternative: direct multipart upload in the submission request (rejected: poor offline
   retry/partial-failure behavior).

5. **Geodesic distance uses Vincenty inverse on WGS84 with a haversine fallback.** Geo flags are advisory indicators
   (accuracy, fix age, clock drift, distance); the UI must not present them as proof against spoofing.

6. **Quantity conversion is strict Decimal arithmetic at gram precision.** kg is canonical; bag conversion requires an
   admin-configured `kg_per_bag` and otherwise returns a 422. No silent rounding or float math.

7. **Ledger integrity is database-backed.** Row locks plus unique idempotency keys guard postings; CHECK constraints
   encode movement-sign/type implications; corrections are compensating reversals. There is no update/delete path for
   movements or audit events.

8. **Admin CSV export is an audited read.** Export uses the same scoped queries as the analytics screens and writes an
   audit event; the client downloads the blob with the bearer token rather than a public URL.

9. **Map without tiles is honest.** When `VITE_MAP_STYLE_URL` is unset, the map page renders a labelled coordinate
   board with real site data instead of fake tiles, pins, or screenshots.

10. **Dependency upgrades for security advisories.** `maplibre-gl` was upgraded 5.x → 6.15 and `vitest` 3.x → 4.1 to
    clear critical `npm audit` findings. Typecheck, tests, lint and production build were re-run after the upgrades;
    `npm audit` reports 0 vulnerabilities. The Vite config now references `vitest/config` types for Vitest 4.

11. **Test-environment workarounds are isolated to test setup.** This workstation auto-loads ROS pytest plugins, so the
    Makefile sets `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`; the suite is synchronous. Node 25's experimental `localStorage`
    shadows jsdom's implementation, so `vitest.setup.ts` installs an in-memory `Storage` only when needed. Production
    code has no test-only branches.

12. **Same-origin deployment shape.** nginx serves the built SPA and proxies `/api/` to the API, with Vite build args as
    the only browser-visible configuration. This keeps the refresh cookie first-party and avoids CORS in the default
    compose topology. Docker images were authored but not built in this environment (no Docker daemon); both
    Dockerfiles pass `hadolint` 2.15.1 and images use a fixed numeric unprivileged UID.

13. **Production/staging configuration fails startup.** `get_settings()` calls `assert_secure_settings()`, which raises
    `RuntimeError` (listing problems only, never secret values) for a placeholder secret, insecure cookies, wildcard
    CORS with credentials, or local/missing S3 evidence storage. Four tests in `tests/test_config_security.py` cover the
    production rejection/acceptance paths, staging rejection and development defaults. This closes the gap between the
    deployment runbook wording and the previous log-only behavior.

14. **Runtime dependency completeness is verified separately from dev tooling.** `email-validator` (needed by pydantic
    `EmailStr` at import time) is pinned in both `pyproject.toml` and `requirements.txt`. A fresh venv with only runtime
    requirements imported the app and completed a login/refresh/me smoke test; this catches packaging gaps that a
    developer venv can hide. The first-admin CLI now validates emails with the same `EmailStr` rules as the API.

15. **Browser E2E uses a disposable database and per-run credentials.** Playwright starts the real FastAPI and Vite
    processes against a dedicated `corn_tracker_e2e` database. Global setup drops/recreates it, runs Alembic, generates
    random admin/distributor passwords in the gitignored `apps/web/e2e/.state/` directory, and bootstraps the first admin;
    a setup project then creates campaign/site/invitation/assignment/stock through the public API. Fixed test identities
    are synthetic (`@e2e.example.org`), no real data or credentials are committed, and deleting the E2E database is the
    explicit reset. The suite is serial and local-only because it needs PostgreSQL with CREATEDB plus Chromium.
    Verified: 7 passed (2 setup + 5 workflow).

16. **E2E caught two defects that unit tests missed.** (a) The distributor assignment list nested a partial site object
    that did not satisfy the declared `SiteOut` shape, so the endpoint returned 500 and never loaded assigned sites; the
    service now returns the complete site summary (admin-only notes remain `None`) with an RBAC/contract regression test.
    (b) A captured geolocation fix was only written to the offline draft at submit, so the UI still said “no fix captured”
    and a reload lost it; the draft now persists the fix immediately and a component test covers it. These fixes are part
    of the E2E-driven release verification, not test-only shims.
