# Corn Distribution Tracker

Monorepo reference implementation of a corn distribution tracker: a **React 19 + TypeScript** single-page app and a **Django 5.2 + Django REST Framework + PostgreSQL** API. It implements the contracts in [`docs/`](docs/) — append-only stock ledger, geotagged evidence, reviewer workflow, offline-safe distributor drafts, and an auditable admin surface.

> **Two editions:** the full application documented below remains unchanged. A deliberately simple, server-rendered Django/SQLite edition lives in the sibling folder [`../corn-distribution-tracker-lite`](../corn-distribution-tracker-lite). It shares the core workflow and visual language, runs on port `8001`, and documents its reduced scope and limitations in its own README.

## What is implemented

**Authentication and roles**
- Email/password login with Argon2id hashing and a database-backed Django session.
- HttpOnly `sessionid` cookie, CSRF double-submit for authenticated unsafe requests, and server-side session revocation on logout/deactivation.
- Per-IP sign-in throttling counts failed attempts only; a `429` shows the server's retry window instead of blaming the password.
- Invitation, password-reset and password-change flows. Invitation links are shown once to the creating admin; password-reset links are issued by an operator because no mail transport ships.
- Server-authoritative RBAC (`ADMIN`, `DISTRIBUTOR`); UI guards are supplementary only.

**Admin**
- Dashboard with KPI cards, delivery progress, review queue, distributor performance and recent audit events.
- Delivery map (MapLibre with OpenStreetMap streets and an Esri satellite toggle by default, or a configured public style URL; labelled coordinate fallback if the map cannot start). It plots only distributor-recorded locations tied to submitted or approved deliveries — never site reference coordinates, sites without deliveries, rejected/cancelled claims or the admin's current position. Campaign filter, synchronized delivery list, and delivery drawer with OpenStreetMap/Google Maps links and an evidence-review link; list-first on mobile.
- Campaigns, targets and assignment planning; distributor invitations/management; campaign-scoped sites created by name during setup, with optional location added later.
- Inventory: receipts, allocations, loss/return adjustments (reason + double confirmation), reversal flow, idempotency keys, append-only ledger view.
- Evidence review: private images through short-lived signed URLs, a street/satellite map of the distributor-reported fix against the site coordinates, OpenStreetMap/Google Maps links, approve (manual, from any recorded place; posts the stock movement server-side), reject, cancel, and exception approvals only for non-location evidence integrity or an exceeded target.
- Analytics with server-computed scopes, accessible tables + CSS bars, and an audited CSV export.
- Organization settings (allowlisted PATCH fields) and append-only audit trail.

**Distributor**
- Assigned sites with targets/approved/pending/remaining and last-visit context.
- Delivery submission: camera/file photo evidence (JPEG/PNG/WebP, 10 MB cap), device-fix capture with accuracy metadata, unit selection (kg/quintal/tonne/bag), draft auto-save, and duplicate-submit guard.
- Drafts & sync screen: `LOCAL_DRAFT → QUEUED → UPLOADING → SUBMITTED` with honest labels, persistent idempotency keys, per-draft retry, sync-all, photo counts, and confirmed discard/removal.
- Submission history with status, review reason, evidence-integrity flags and evidence status.

**Backend invariants**
- Quantities are decimals stored as kg; API contract exposes them as strings.
- Stock movements and audit events are append-only; PostgreSQL triggers reject updates/deletes and corrections use compensating reversals.
- Idempotency keys are unique per operation; concurrent ledger writes use row locks.
- Evidence is private (local dev storage or S3-compatible), SHA-256 hashed, and viewed through short-lived signed URLs.
- Location context (coordinates, accuracy, timestamp, optional distance) is recorded but never gates approval. Non-location evidence-integrity flags (duplicate hash, capture-time drift, unexpected file type) are advisory indicators — explicitly **not** proof against spoofing.
- Production startup fails fast on a sample/short secret, insecure cookies, wildcard CORS with credentials or non-S3/missing storage configuration.

## Repository layout

```text
apps/api            Django/DRF app, migrations, management commands, tests (66 tests)
apps/web            React SPA, Vitest tests (37 tests), Playwright E2E suite (8 tests)
docs/               Product/API/design/offline/ops contracts (source of truth)
handoffs/           File ownership map + per-file implementation notes
Makefile            Developer commands
.env.example        Configuration template (copy to .env)
```

## Prerequisites

- Node.js 22+ and npm.
- Python 3.12+ (this build was validated in a CPython **3.14** virtualenv).
- PostgreSQL 13+ (validated on PostgreSQL 17). PostGIS is **not** required.
- No container runtime is required for the documented local workflow.

## Local development (verified commands)

```bash
# 1. Configuration
cp .env.example .env
# Review .env. The template points at postgresql+psycopg://corn:corn@localhost:5432/corn_tracker.
# Use an existing PostgreSQL role/database or create one, then update DATABASE_URL.

# 2. Backend
make api-install               # creates .venv and installs runtime + dev requirements
make migrate                   # applies Django migrations
make create-admin ARGS="--email admin@example.org"   # interactive password prompt
make run-api                   # http://localhost:8000

# 3. Frontend (new terminal)
make web-install               # npm ci
make run-web                   # http://localhost:5173; Vite proxies /api → http://localhost:8000
```

Health checks (unauthenticated):

```bash
make health
# or
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

`make run-api` binds to `127.0.0.1:8000`. Vite runs on `5173` with a same-origin proxy to the API, so the HttpOnly session cookie stays first-party in development.

The default `.env` values are local-development-only. Production startup fails fast on a sample/short secret, insecure cookies, wildcard CORS with credentials, or non-S3/missing storage configuration; see [`docs/ops/ENVIRONMENT_VARIABLES.md`](docs/ops/ENVIRONMENT_VARIABLES.md).

### Invitations and password resets in this build

There is no mail transport. When an admin creates a distributor invitation, the API returns the raw invite token **once** and the UI shows a one-time link that the admin must deliver through a secure channel. It is never logged and cannot be retrieved again.

Password reset is operator-delivered:

```bash
cd apps/api
../../.venv/bin/python manage.py issue_password_reset \
  --email distributor@example.org \
  --web-base-url http://localhost:5173
```

The command prints a single-use token/link valid for one hour. The public forgot-password form records the request without revealing whether an account exists and states plainly that an operator will supply the link.

### Browser E2E (verified locally)

```bash
make e2e-install   # one-time Chromium install
make test-e2e      # ports 8000 and 5173 must be free
```

`npm run test:e2e` runs `e2e/support/run-e2e.mjs`, which recreates the isolated database and applies Django migrations **before** Playwright starts its web servers. Playwright then starts real Django and Vite, creates per-run credentials and seeds the synthetic world through public HTTP APIs.

- Default database: `postgresql+psycopg://corn:corn@localhost:5432/corn_tracker_e2e`. **The suite drops and recreates this database**; never point `E2E_DATABASE_URL` at real data. The database name must contain `e2e`, and the connecting role must own it or be able to create/drop it.
- Overrides: `E2E_DATABASE_URL`, `E2E_PYTHON`, and `E2E_LOCAL_STORAGE_DIR` (default `/tmp/corn-tracker-e2e-storage`).
- Each run generates random admin/distributor passwords in the gitignored `apps/web/e2e/.state/` directory. No credentials or real data are committed.
- Covered flow: session-cookie restore and role guard; photo/geolocation submission; private evidence rendering; admin approval posting the ledger movement; distributor view of the approved record; offline draft staying `QUEUED` and syncing only after connectivity returns; and a 360 px mobile-viewport overflow check.

## Verification (run through 2026-10-28)

| Command | Result |
|---|---|
| `make test-api` (sets `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`) | **98 passed** |
| `make lint-api` (ruff 0.17.1) | **All checks passed** |
| `make typecheck-api` (mypy 2.4.0 + django-stubs 5.2.9) | **No issues in 51 source files** |
| `python manage.py makemigrations --check --dry-run` | **No changes detected** |
| `npx tsc -b --noEmit` (web) | **passed** |
| `npm test` (Vitest 4.1.12) | **39 passed** across 7 files |
| `npm run lint` (ESLint 9 + typescript-eslint + react-hooks) | **0 errors, 0 warnings** |
| `npm run build` | **passed** — app JS 520.54 kB (`gzip 156.21 kB`), CSS 104.49 kB (`gzip 16.95 kB`); MapLibre chunk 1,094.99 kB (`gzip 298.42 kB`); Vite warns about large chunks |
| `npm audit --audit-level=high` | **0 vulnerabilities** |
| `make test-e2e` (Playwright 1.64.1, Chromium, real Django + PostgreSQL) | **9 passed** (2 setup + 7 workflow) |
| `gunicorn --check-config config.wsgi:application` | **passed** |
| `python manage.py check` | **No issues identified** |
| `python manage.py check --deploy` | **6 expected local-configuration warnings** — HSTS, SSL redirect, development secret, secure session/CSRF cookies and DEBUG are environment/ingress-owned. Production startup fails fast for the secret, secure cookies, DEBUG, unsafe CORS and non-S3 storage; HSTS and SSL redirect must still be set/verified at deployment. The prior missing-frame-middleware warning is fixed. |
| `make check` | **passed** locally (all API/web lint, type, migration, test and production-build gates) |
| CI workflow (`.github/workflows/ci.yml`) | **present and YAML-validated locally** — backend, frontend, Playwright E2E and dependency review jobs; not yet executed on GitHub because changes are uncommitted |
| Native local smoke (Django `runserver` + Vite) | **passed** — `/health/live`, `/health/ready`, login page and session bootstrap reachable on `localhost:8000` / `localhost:5173` |
| 360 px screenshot audit (current screens) | **scrollWidth 360; heading clear of the top bar; no horizontal overflow, unexpected console errors or 5xx responses** |
| Local Django-schema backup/restore drill (synthetic E2E DB) | **passed** — 85,778-byte dump; migrations `0001`–`0004` restored; users 2/2, campaigns 1/1, sites 1/1, assignments 1/1, records 2/2, evidence 2/2, movements 3/3, audit 24/24, accounts 3/3; append-only trigger present; 0 missing evidence objects |
| Simulated S3-compatible evidence drill (external audit probe) | **passed** — presigned PUT, CORS preflight, SSE header, completion, attachment, same-size and oversized tamper rejection against a local S3 emulator; real provider/CORS verification remains operator-owned |

Environment note: this workstation auto-loads ROS pytest plugins into any pytest invocation, which is why `make test-api` disables plugin autoload. The test suite uses Django's test client against a temporary PostgreSQL database and is synchronous. Docker/Podman/nginx runtime validation is unavailable here; container/nginx files are statically checked only.

### Map/location update (verified 2026-10-25)

| Command | Result |
|---|---|
| `npx tsc -b --noEmit` (web) | **passed** |
| `npx eslint src --max-warnings=0` | **0 errors, 0 warnings** |
| `npm test` (Vitest 4.1.12) | **34 passed** across 5 files (9 map tests) |
| `npm run build` | **passed** — worker asset emitted; MapLibre chunk 1,094.99 kB (`gzip 298.42 kB`); existing >500 kB warning still applies |
| Headless Chromium smoke against dev servers | **passed** (site-map UI, superseded by the delivery-only map below) — 28 OSM street tile requests and 15 Esri satellite tile requests, all `200`; Map/Satellite toggled attribution correctly; “My location” with a mocked New Delhi position recentered the satellite map on Delhi and rendered the location marker; site drawer and evidence review showed exact-coordinate Google Maps links. Only console error was the expected pre-login `/auth/me` `401`. |

### Phone/HTTPS verification (2026-10-25)

| Check | Result |
|---|---|
| HTTPS Cloudflare quick tunnel → Django/Vite | **passed** — login as `amina@example.org`, `/my-sites`, and `/deliver/new` all worked through the tunnel. |
| Distributor geolocation over HTTPS | **passed** — mocked Delhi fix captured as `28.613900, 77.209000 ±12.0 m`; no permission-denied message. |
| Insecure HTTP origin guard | **passed** — component test shows a specific “Location needs HTTPS” message instead of a misleading permission denial. |
| Saved-fix reload/submit | **passed** — a captured fix survived a remount, the form stopped showing a false “Location not captured” warning, and the submission payload kept the coordinates. |
| Admin location display | **passed** — review labels a fix **Captured** or **Missing** without a location warning; only non-location evidence-integrity flags are shown. |
| Large phone-style upload | **passed** — authenticated 7.0 MB JPEG upload returned `204` after raising the raw-body ceiling; test intent/object cleaned up. |
| Backend tests | **98 passed**; `make test-api`. |

### Phone / HTTPS development

Phone browsers require a **secure context** for `navigator.geolocation`. Opening the LAN URL (`http://192.168.x.x:5173`) lets the UI and login work, but GPS capture is blocked even when the browser's site permission says “Allow”. Use HTTPS for the distributor phone workflow.

For a short-lived development demo, an HTTPS tunnel (for example Cloudflare Quick Tunnel) is sufficient. Add the tunnel hostname to Django `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`, and use a Vite `server.allowedHosts` entry for the tunnel domain; this repository allows `.trycloudflare.com` in development. Quick tunnels are public and temporary, so use only synthetic/demo data, keep authentication on, and stop the tunnel when finished. For a production or real-data deployment, use a proper HTTPS reverse proxy with a trusted certificate instead.

`DATA_UPLOAD_MAX_MEMORY_SIZE` is derived as `MAX_EVIDENCE_UPLOAD_BYTES + 1 MiB`; the service still enforces the configured evidence cap.

### Campaign-site update (2026-10-25)

Sites are now configured inside a campaign. The admin sidebar no longer has a **Sites** item; `/sites` redirects to `/campaigns`. The campaign create form accepts optional site names (one per line), and selecting a campaign opens a site panel for adding more names and setting or editing an optional latitude/longitude later. A generated `site_code` is used when none is supplied. A name-only site remains assignable; submissions still capture GPS when available, but location quality and distance/geofence never block or warn. The delivery map plots the record's captured fix and does not need site coordinates; evidence review simply omits the site reference marker. Existing submissions are never recalculated when coordinates are added later.

`python manage.py migrate` applied `corn.0003_campaign_sites_optional_location` to the development database. Existing sites were backfilled from their earliest assignment campaign; no coordinates were invented. API tests cover campaign-site creation, generated codes, duplicate names, optional/cleared locations, cross-campaign assignment rejection, campaign-scoped analytics/map filtering and geo evaluation without site coordinates. Web tests cover campaign-dialog site creation, adding a name-only site from the selected campaign, and adding a location later. Superseded verification at that update: `make test-api` → 66 passed, `npm test` → 37 passed across 6 files, `make test-e2e` → 8 passed. Current counts are in the verification table above.

### Delivery-only map update (verified 2026-10-25)

The admin map now plots **only distributor-recorded delivery locations**. `GET /analytics/map-deliveries` returns one point per delivery with a captured fix and status `SUBMITTED` or `APPROVED`; rejected/cancelled claims are excluded. The page no longer plots site reference coordinates, sites without deliveries or an admin “My location” marker. Its synchronized list shows site, distributor, status, quantity and submitted time; selecting an entry opens captured coordinates/accuracy, OpenStreetMap/Google Maps links and the evidence-review workspace. The retained approved 1 kg Kolhapur record therefore appears even though its site is name-only.

Verification: `make test-api` → **98 passed**; `make test-web` → **39 passed across 7 files**; `make lint-api` / `make typecheck-api` / `make migrate-check` clean; `npm run typecheck` / `npm run lint` / `npm run build` clean; `make test-e2e` → **9 passed** (2 setup + 7 workflow). New tests cover delivery-only filtering, status/bbox/authorization, rejected-claim exclusion, the approved-record point, delivery list/map labels, drawer links, the empty state and a real-browser assertion that the approved E2E delivery appears as a delivery point with no site list. A headless Chromium smoke against the running dev stack rendered the current two approved Kolhapur delivery points as two list entries and two map pins, opened the drawer with coordinates/map/evidence links, showed no “Sites in scope” section, and logged no console errors or non-tile request failures. There is no committed test for the WebGL/tile-fallback rendering path.

### Manual smoke checklist

1. Sign in as the admin you created; create a campaign with two site names (no coordinates needed) and invite a distributor.
2. Record a receipt for central stock, then allocate kg to the distributor.
3. Sign in as the distributor (separately-created account), open **My sites → New delivery update**.
4. Attach a photo, optionally capture location (submission works with or without it), enter a quantity, submit.
5. Back as admin, open **Evidence review**, inspect the private image, then **approve** — the site stock movement is posted and visible in the ledger.
6. Go offline (devtools) as the distributor, save a draft and submit: the draft stays **Queued to sync**, never “Submitted”. Reconnect and retry.
7. Open **Settings**, set a bag conversion, save, reload, then disable it and confirm the regression to kg/null.

## Configuration notes

For the managed Railway backend plus Vercel frontend path, see
[`docs/ops/RAILWAY_VERCEL_DEPLOYMENT.md`](docs/ops/RAILWAY_VERCEL_DEPLOYMENT.md).
The frontend build intentionally fails on Vercel while
`apps/web/vercel.json` still contains the Railway placeholder origin.

- Only `VITE_*` values are shipped to the browser. Never put secrets behind that prefix.
- `VITE_API_BASE_URL` defaults to `/api/v1` (same-origin, works with the Vite proxy and a reverse proxy). For a cross-origin SPA, set it at build time and configure `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` and cookie settings.
- `VITE_MAP_STYLE_URL` is optional. Empty → MapLibre renders OpenStreetMap streets plus an Esri satellite toggle by default; configured → MapLibre loads your public vector/raster style and the built-in toggle is hidden. `VITE_MAP_TILE_URL` overrides only the default street raster template, and `VITE_MAP_SATELLITE_TILE_URL` overrides the satellite template. If the map cannot initialize, the labelled coordinate board is used. Exact-coordinate Google Maps links require no key; embedding Google Maps itself would require a Google Maps API key and billing.
- Evidence storage: `STORAGE_MODE=local` is for development/testing; production requires an S3-compatible bucket (`STORAGE_*`).
- Signed evidence URLs expire (`STORAGE_SIGNED_URL_TTL_SECONDS`, default 120 s).
- There is no OpenAPI UI endpoint; [`docs/architecture/API_CONTRACT.md`](docs/architecture/API_CONTRACT.md) is the API source of truth.

## Known limitations (honest list)

- **No mail transport.** Invitations expose a one-time link to the creating admin; password resets require an operator command and a secure delivery channel.
- **Public map tiles are development/small-scale defaults.** OpenStreetMap's [tile usage policy](https://operations.osmfoundation.org/policies/tiles/) does not permit high-volume or heavy app traffic, and the public Esri World Imagery service is similarly not a substitute for a licensed production agreement. Point `VITE_MAP_TILE_URL`, `VITE_MAP_SATELLITE_TILE_URL` or `VITE_MAP_STYLE_URL` at your own tile server or a provider that permits your volume before broad rollout. The coordinate board remains the fallback when map initialization fails.
- **Google Maps is not embedded.** It is generally the most accurate consumer map in India, but its JavaScript/embed APIs require a key and billing. The app therefore offers exact-coordinate Google Maps links and a no-key satellite layer; a Google Maps JS integration is a follow-up if a key is supplied.
- **Development data is intentionally minimal.** The local database keeps the Kolhapur campaign/site, Amina's active assignment, the approved 1 kg Kolhapur record with its funding ledger chain, organization settings (Asia/Kolkata) and all three user logins. Juba demo data and newer phone submissions were removed after a database/private-storage backup. Create new campaigns/sites for further testing; do not expect old demo rows.
- **The admin map shows delivery points only.** Submitted and approved delivery records with a captured fix appear; rejected/cancelled claims, site reference coordinates, sites without deliveries and the admin's current position do not. UI filtering is campaign-only; the API also accepts a bounding box and distributor id, but status/date filters and marker clustering are not implemented.
- **No map preview on the admin overview.** The overview links to the full map page.
- **Evidence review is a single-record workspace.** Previous/next review navigation is not implemented. The location map compares the reported fix with the site's *current* coordinates, not a historical site snapshot; for a name-only site the site marker is omitted. Location is Captured/Missing only and does not block approval.
- **No image thumbnails.** The private original is loaded through an authorized signed URL.
- **No in-app notifications or Profile/Help screen.** Assignment and review state is visible on the relevant screens; there is no notification feed.
- **No re-invite or password reset from the distributor list.** Invitations are for new accounts; an operator issues reset links.
- **Inventory forms post kilograms.** The API accepts `KG`, `QUINTAL`, `TONNE` and `BAG` for receipts/allocations/adjustments, but the current admin form does not expose the unit selector.
- **Admin list filters are limited.** Campaigns expose a status filter; evidence and audit expose the filters shown on each screen. Sites are managed inside the selected campaign and have no separate search page. Several tables load a bounded first page (25 or 100 rows) and sort client-side rather than exposing pagination controls.
- **Analytics filters are campaign + UTC date range.** Status/distributor/site filters and URL-persisted filter state are not implemented.
- **GPS/EXIF are advisory.** Coordinates, accuracy, timestamps and optional distance are recorded; location quality is not a warning or gate. Duplicate hash, capture-time drift and unexpected file type are the only evidence-integrity flags. Sophisticated spoofing is not detectable by this design.
- **Offline drafts are plaintext local browser data.** Local drafts persist in `localStorage` and attached blobs in IndexedDB; the UI no longer claims encryption at rest. After a successful sync, submitted draft metadata is scrubbed and local photos are deleted; stale local drafts are pruned after 24 hours. In environments without IndexedDB (some test shells), the store falls back to memory and attached blobs do not survive a reload.
- **BAG conversions** require an admin-configured `kg_per_bag`; the API rejects bag quantities otherwise.
- **No MFA yet.** Admin MFA should be required/assessed before broad production rollout; the current build is password + session based.
- **No malware scanner.** Evidence uploads are size/type restricted, decoded, content-sniffed and hashed; integrate a scanning hook before accepting untrusted public uploads at scale.
- **No metrics/APM/alerting integration is bundled.** Structured request logs, request IDs and liveness/readiness checks are implemented, but production dashboards/alerts must be wired by the operator.
- **Rate limits are process-local.** The in-memory bucket table is bounded, but multiple Gunicorn workers or replicas each enforce their own counters; use a shared Redis/cache limiter before horizontal scale-out.
- **No automatic evidence-retention job.** Configure bucket lifecycle/retention and database backup retention operationally; see [`docs/ops/BACKUP_RESTORE.md`](docs/ops/BACKUP_RESTORE.md). The local restore drill does not replace a production-provider drill.
- **Real S3/provider CORS is unverified.** The direct-upload path, SSE header, CORS preflight, completion, same-size replacement and oversized replacement pass against a local S3-compatible emulator, and the CORS requirements are documented; verify them against the chosen bucket before launch.
- **Pre-upgrade idempotency keys fail closed.** Migration `0004` scopes legacy keys but existing rows have no request fingerprint, so a retry using one returns `409` rather than risking an unrelated replay. Re-key clients/offline drafts during the upgrade window.
- **Single organization** by design; multi-tenancy would require explicit row-level isolation and tests.
- **Browser E2E** needs a PostgreSQL role allowed to create/drop the isolated E2E database plus Playwright Chromium. It is wired into the CI workflow and passes locally; the workflow has not run on GitHub yet because these changes are uncommitted. The flow covers the critical submission/review/offline path and one 360 px viewport test. A separate screenshot audit covered every current screen at 360 px, but neither replaces real-device or assistive-technology testing.
- **Container/nginx runtime verification is unavailable** in this workspace. Compose, nginx, Dockerfile and Gunicorn configuration were statically validated; build and run them in staging.
- **One JS chunk exceeds Vite's 500 kB warning threshold**; code-splitting the map/route bundle is a reasonable next optimization.

## Documentation index

- [`docs/architecture/API_CONTRACT.md`](docs/architecture/API_CONTRACT.md) — endpoints, enums, error envelope.
- [`docs/architecture/OFFLINE_SYNC.md`](docs/architecture/OFFLINE_SYNC.md) — draft states, idempotency, account switching.
- [`docs/design/SCREEN_SPECS.md`](docs/design/SCREEN_SPECS.md) — screen-by-screen behaviour and copy rules.
- [`docs/design/DESIGN_SYSTEM.md`](docs/design/DESIGN_SYSTEM.md) — tokens, components, accessibility.
- [`docs/ops/ENVIRONMENT_VARIABLES.md`](docs/ops/ENVIRONMENT_VARIABLES.md) — every setting and its security constraints.
- [`docs/ops/BACKUP_RESTORE.md`](docs/ops/BACKUP_RESTORE.md) — database/evidence backup, restore verification and retention.
- [`docs/ops/IMPLEMENTATION_DECISIONS.md`](docs/ops/IMPLEMENTATION_DECISIONS.md) — decision log, including implementation additions.
- [`handoffs/file_map.md`](handoffs/file_map.md) — per-file ownership, status, and implementation notes.
