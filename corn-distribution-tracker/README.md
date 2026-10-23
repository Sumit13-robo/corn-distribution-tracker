# Corn Distribution Tracker

Monorepo reference implementation of a corn distribution tracker: a **React 19 + TypeScript** single-page app and a **Django 5.2 + Django REST Framework + PostgreSQL** API. It implements the contracts in [`docs/`](docs/) — append-only stock ledger, geotagged evidence, reviewer workflow, offline-safe distributor drafts, and an auditable admin surface.

## What is implemented

**Authentication and roles**
- Email/password login with Argon2id hashing and a database-backed Django session.
- HttpOnly `sessionid` cookie, CSRF double-submit for unsafe requests, and server-side session revocation on logout/deactivation.
- Per-IP sign-in throttling counts failed attempts only; a `429` shows the server's retry window instead of blaming the password.
- Invitation, password-reset and password-change flows. Invitation links are shown once to the creating admin; password-reset links are issued by an operator because no mail transport ships.
- Server-authoritative RBAC (`ADMIN`, `DISTRIBUTOR`); UI guards are supplementary only.

**Admin**
- Dashboard with KPIs, review queue, distributor performance and recent audit events.
- Distribution map (MapLibre when a style URL is configured, otherwise a labelled coordinate fallback — no fake tiles or pins). List-first on mobile.
- Campaigns, targets and assignment planning; distributors/invitations; site management with progress history.
- Inventory: receipts, allocations, loss/return adjustments (reason + double confirmation), reversal flow, idempotency keys, append-only ledger view.
- Evidence review: private thumbnails via short-lived URLs, approve (posts the stock movement server-side), reject, cancel, exception approvals.
- Analytics with server-computed scopes, accessible tables + CSS bars, and an audited CSV export.
- Organization settings (allowlisted PATCH fields) and append-only audit trail.

**Distributor**
- Assigned sites with targets/approved/pending/remaining and due dates.
- Delivery submission: camera/file photo evidence (JPEG/PNG/WebP, 10 MB cap), device-fix capture with accuracy metadata, unit selection (kg/quintal/tonne/bag), draft auto-save, and duplicate-submit guard.
- Drafts & sync screen: `LOCAL_DRAFT → QUEUED → UPLOADING → SUBMITTED` with honest labels, persistent idempotency keys, per-draft retry, sync-all, photo counts, and confirmed discard/removal.
- Submission history with status, review reason, geo flags and evidence status.

**Backend invariants**
- Quantities are decimals stored as kg; API contract exposes them as strings.
- Stock movements and audit events are append-only; PostgreSQL triggers reject updates/deletes and corrections use compensating reversals.
- Idempotency keys are unique per operation; concurrent ledger writes use row locks.
- Evidence is private (local dev storage or S3-compatible), SHA-256 hashed, and viewed through short-lived signed URLs.
- Geo metadata (accuracy, age, distance) is recorded and flagged as an indicator — explicitly **not** proof against spoofing.
- Production startup fails fast on insecure secrets, cookies, CORS/CSRF origins or storage configuration.

## Repository layout

```text
apps/api            Django/DRF app, migrations, management commands, tests (60 tests)
apps/web            React SPA, Vitest tests (23 tests), Playwright E2E suite (8 tests)
docs/               Product/API/design/offline/ops contracts (source of truth)
handoffs/           File ownership map + per-file implementation notes
docker-compose.yml  PostgreSQL 17 + Django/Gunicorn API + nginx-served SPA
Makefile            Developer commands
.env.example        Configuration template (copy to .env)
```

## Prerequisites

- Node.js 22+ and npm.
- Python 3.12+ (this build was validated in a CPython **3.14** virtualenv; the API image uses `python:3.14-slim`).
- PostgreSQL 13+ (validated on PostgreSQL 17). PostGIS is **not** required.
- Docker is optional.

## Option A — Docker Compose

```bash
cp .env.example .env
# Review .env: set a real SECRET_KEY for anything beyond local development.

docker compose up --build
```

- Web UI: <http://localhost:5173> (nginx serves the SPA and proxies `/api/` to the API, keeping the session cookie first-party).
- API: <http://localhost:8000> · liveness <http://localhost:8000/health/live> · readiness <http://localhost:8000/health/ready>.
- The API container runs `python manage.py migrate --noinput`, then Gunicorn (`config.wsgi:application`).

Create the first administrator (one-time; refuses if an admin already exists):

```bash
docker compose exec api python manage.py create_admin --email admin@example.org
# prompts for the password; it can also come from the env var named by --password-env
```

> **Honest status:** the Dockerfiles and nginx config are committed and the compose wiring is consistent, but **Docker was not available on the machine where this repo was finished**, so the images were not built or started here. The non-Docker path below was executed end-to-end (tests, lint, typecheck, production build, Django migrations, browser E2E, 360 px audit, backup/restore drill).

## Option B — Local development (verified commands)

```bash
# 1. Configuration
cp .env.example .env

# 2. Backend
make api-install               # creates .venv and installs runtime + dev requirements
# Start PostgreSQL matching DATABASE_URL, e.g. `make db-up` (Docker) or your local instance
make migrate
make create-admin ARGS="--email admin@example.org"   # interactive password prompt
make run-api                   # http://localhost:8000

# 3. Frontend (new terminal)
make web-install               # npm ci
make run-web                   # http://localhost:5173; Vite proxies /api → http://localhost:8000
```

The default `.env` values are local-development-only. Production startup fails fast if required secrets are missing or insecure settings are used; see [`docs/ops/ENVIRONMENT_VARIABLES.md`](docs/ops/ENVIRONMENT_VARIABLES.md).

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

## Verification (run on 2026-10-23)

| Command | Result |
|---|---|
| `make test-api` (sets `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`) | **60 passed** |
| `make lint-api` (ruff 0.17.1) | **All checks passed** |
| `make typecheck-api` (mypy 2.4.0 + django-stubs 5.2.9) | **No issues in 49 source files** |
| `python manage.py makemigrations --check --dry-run` | **No changes detected** |
| `npx tsc -b --noEmit` (web) | **passed** |
| `npm test -- --run` (Vitest 4.1.12) | **23 passed** across 4 files |
| `npm run lint` (ESLint 9 + typescript-eslint + react-hooks) | **0 errors, 0 warnings** |
| `npm run build` | **passed** — `dist` JS 513.50 kB (`gzip 152.53 kB`), CSS 31.10 kB; Vite warns one chunk exceeds 500 kB |
| `make test:e2e` (Playwright 1.64.1, Chromium, real Django + PostgreSQL) | **8 passed** (2 setup + 6 workflow) |
| `gunicorn --check-config config.wsgi:application` | **passed** |
| `python manage.py check` | **No issues identified** |
| 360 px screenshot audit (20 screens: login + 3 reset modes + 11 admin + 5 distributor) | **scrollWidth 360; heading clear of the top bar; no horizontal overflow, unexpected console errors or 5xx responses** |
| Browser interaction checks at 360 px | one-time invitation link dialog, audit `auth.login` filter, local draft discard, settings bag-factor round-trip, drawer scroll lock/Escape/focus restore |
| Settings round-trip in browser | bag factor `50.00` saved; disabling sends `kg_per_bag: null` and persists after reload |
| Local Django-schema backup/restore drill (synthetic E2E DB) | **passed** — 83,441-byte dump; both corn migrations restored; users 2/2, campaigns 1/1, sites 1/1, assignments 1/1, records 2/2, evidence 2/2, movements 3/3, audit 23/23, accounts 3/3; 0 missing evidence objects |
| Docker image build + `docker compose up` | **Not executed** — no Docker/Podman daemon on this host |

Environment note: this workstation auto-loads ROS pytest plugins into any pytest invocation, which is why `make test-api` disables plugin autoload. The test suite uses Django's test client against a temporary PostgreSQL database and is synchronous.

### Manual smoke checklist

1. Sign in as the seeded admin; create a campaign, two sites and a distributor invitation.
2. Record a receipt for central stock, then allocate kg to the distributor.
3. Sign in as the distributor (separately-created account), open **My sites → New delivery update**.
4. Attach a photo, capture location (or submit without it and observe the honest warning), enter a quantity, submit.
5. Back as admin, open **Evidence review**, inspect the private image, then **approve** — the site stock movement is posted and visible in the ledger.
6. Go offline (devtools) as the distributor, save a draft and submit: the draft stays **Queued to sync**, never “Submitted”. Reconnect and retry.
7. Open **Settings**, set a bag conversion, save, reload, then disable it and confirm the regression to kg/null.

## Configuration notes

- Only `VITE_*` values are shipped to the browser. Never put secrets behind that prefix.
- `VITE_API_BASE_URL` defaults to `/api/v1` (same-origin, works with the Vite proxy and nginx). For a cross-origin SPA, set it at build time and configure `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` and cookie settings.
- `VITE_MAP_STYLE_URL` is optional. Empty → the map page renders a coordinate board with real site data; configured → MapLibre loads your public style.
- Evidence storage: `STORAGE_MODE=local` is for development/testing; production requires an S3-compatible bucket (`STORAGE_*`).
- Signed evidence URLs expire (`STORAGE_SIGNED_URL_TTL_SECONDS`, default 120 s).
- There is no OpenAPI UI endpoint; [`docs/architecture/API_CONTRACT.md`](docs/architecture/API_CONTRACT.md) is the API source of truth.

## Known limitations (honest list)

- **Docker images were not built** in this environment (no Docker/Podman daemon; user namespaces are blocked). Dockerfile/Compose runtime validation remains pending on a Docker-capable host.
- **No mail transport.** Invitations expose a one-time link to the creating admin; password resets require an operator command and a secure delivery channel.
- **No live map tiles without configuration** — the fallback board is deliberate; nothing is mocked.
- **GPS/EXIF are advisory.** Accuracy, fix age, clock drift and distance are recorded and flagged; sophisticated spoofing is not detectable by this design.
- **Offline photos** live in IndexedDB and survive reloads in real browsers. In environments without IndexedDB (some test shells), the store falls back to memory — drafts persist in `localStorage`, but attached blobs do not survive a reload.
- **BAG conversions** require an admin-configured `kg_per_bag`; the API rejects bag quantities otherwise.
- **No MFA yet.** Admin MFA should be required/assessed before broad production rollout; the current build is password + session based.
- **No malware scanner.** Evidence uploads are size/type restricted, decoded, content-sniffed and hashed; integrate a scanning hook before accepting untrusted public uploads at scale.
- **No metrics/APM/alerting integration is bundled.** Structured request logs, request IDs and liveness/readiness checks are implemented, but production dashboards/alerts must be wired by the operator. Rate limits are process-local.
- **No automatic evidence-retention job.** Configure bucket lifecycle/retention and database backup retention operationally; see [`docs/ops/BACKUP_RESTORE.md`](docs/ops/BACKUP_RESTORE.md). The local restore drill does not replace a production-provider drill.
- **Single organization** by design; multi-tenancy would require explicit row-level isolation and tests.
- **Browser E2E is local-only**: it needs a PostgreSQL role allowed to create/drop the isolated E2E database plus Playwright Chromium; no CI pipeline is shipped. The E2E flow covers the critical submission/review/offline path and one 360 px viewport test. A separate screenshot audit covered every current screen at 360 px, but neither replaces real-device or assistive-technology testing.
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
