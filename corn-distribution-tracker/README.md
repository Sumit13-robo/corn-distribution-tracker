# Corn Distribution Tracker

Monorepo reference implementation of a corn distribution tracker: a **React 19 + TypeScript** single-page app and a **FastAPI + SQLAlchemy 2 + PostgreSQL** API. It implements the contracts in [`docs/`](docs/) — append-only stock ledger, geotagged evidence, reviewer workflow, offline-safe distributor drafts, and an auditable admin surface.

## What is implemented

**Authentication and roles**
- Email/password login with Argon2id hashing; access token kept in memory only.
- HttpOnly refresh cookie with rotation and single-flight refresh in the client (`401 → POST /auth/refresh → retry once`).
- Invitation, password-reset, and password-change flows. Raw invite/reset tokens are never shown in the UI.
- Server-authoritative RBAC (`ADMIN`, `DISTRIBUTOR`); UI guards are supplementary only.

**Admin**
- Dashboard with KPIs, review queue and recent audit events.
- Distribution map (MapLibre when a style URL is configured, otherwise a labelled coordinate fallback — no fake tiles or pins).
- Campaigns, targets and assignment planning; distributors/invitations; site management with progress history.
- Inventory: receipts, allocations, loss/return adjustments (reason + double confirmation), reversal flow, idempotency keys, append-only ledger view.
- Evidence review: private thumbnails via short-lived URLs, approve (posts the stock movement server-side), reject, cancel, exception approvals.
- Analytics with server-computed scopes, accessible tables + CSS bars, and an audited CSV export.
- Organization settings (allowlisted PATCH fields) and immutable audit trail.

**Distributor**
- Assigned sites with targets/approved/pending/remaining and due dates.
- Delivery submission: camera/file photo evidence (JPEG/PNG/WebP, 10 MB cap), device-fix capture with accuracy metadata, unit selection (kg/quintal/tonne/bag), draft auto-save, and duplicate-submit guard.
- Offline drafts: `LOCAL_DRAFT → QUEUED → UPLOADING → SUBMITTED` with honest labels, persistent idempotency keys, automatic retry on reconnect, and keep-or-discard handling at logout.
- Submission history with status, review reason, geo flags, and evidence status.

**Backend invariants**
- Quantities are decimals stored as kg; API contract exposes them as strings.
- Stock movements and audit events are append-only; corrections are compensating reversals enforced with DB constraints.
- Idempotency keys are unique per operation; concurrent ledger writes use row locks.
- Evidence is private (local dev storage or S3-compatible), SHA-256 hashed, and viewed through short-lived signed URLs.
- Geo metadata (accuracy, age, distance) is recorded and flagged as an indicator — explicitly **not** proof against spoofing.

## Repository layout

```text
apps/api            FastAPI app, Alembic migrations, tests (45 tests)
apps/web            React SPA, Vitest tests (13 tests)
docs/               Product/API/design/offline/ops contracts (source of truth)
handoffs/           File ownership map + per-file implementation notes
docker-compose.yml  Postgres (PostGIS image) + API + nginx-served SPA
Makefile            Developer commands
.env.example        Configuration template (copy to .env)
```

## Prerequisites

- Node.js 22+ and npm.
- Python 3.12+ (this build was validated in a CPython **3.14** virtualenv; the API image uses `python:3.14-slim`).
- PostgreSQL 13+ (Docker Compose uses `postgis/postgis:17-3.5`; PostGIS itself is not required by the schema).
- Docker is optional.

## Option A — Docker Compose

```bash
cp .env.example .env
# Review .env: set a real SECRET_KEY for anything beyond local development.

docker compose up --build
```

- Web UI: <http://localhost:5173> (nginx serves the SPA and proxies `/api/` to the API, keeping the refresh cookie first-party).
- API: <http://localhost:8000> · liveness <http://localhost:8000/health/live> · readiness <http://localhost:8000/health/ready> · dev docs <http://localhost:8000/docs>.
- The API container runs `alembic upgrade head` before starting uvicorn.

Create the first administrator (one-time; refuses if an admin already exists):

```bash
docker compose exec api python -m app.cli.create_admin --email admin@example.org
# prompts for the password twice; never passed via the command line
```

> **Honest status:** the Dockerfiles and nginx config are committed and the compose wiring is consistent, but **Docker was not available on the machine where this repo was finished**, so the images were not built here. The non-Docker path below was executed end-to-end (tests, lint, typecheck, production build, migrations).

## Option B — Local development (verified commands)

```bash
# 1. Configuration
cp .env.example .env

# 2. Backend
python3 -m venv .venv
.venv/bin/pip install -r apps/api/requirements.txt -r apps/api/requirements-dev.txt
# Start Postgres matching DATABASE_URL, e.g.: docker compose up -d db
make migrate
make create-admin ARGS="--email admin@example.org"   # interactive password prompt

make run-api        # http://localhost:8000

# 3. Frontend (new terminal)
cd apps/web
npm ci
npm run dev         # http://localhost:5173; Vite proxies /api → http://localhost:8000
```

The default `.env` values are local-development-only. Production startup fails fast if required secrets are missing or insecure settings are used; see [`docs/ops/ENVIRONMENT_VARIABLES.md`](docs/ops/ENVIRONMENT_VARIABLES.md).

### Invitations in this build

`POST /admin/users/invitations` returns the raw invite token **once** so a deployment can hand it to an email/SMS delivery integration. The admin UI intentionally never displays it (per `docs/design/SCREEN_SPECS.md`). No mail transport is shipped; for local evaluation, create invites through a trusted API client when you need the token, or wire your own delivery channel server-side.

## Verification (run on 2026-10-22)

| Command | Result |
|---|---|
| `make test-api` (sets `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`) | **45 passed** |
| `make lint-api` (ruff 0.17.1) | **All checks passed** |
| `make typecheck-api` (mypy 2.4.0) | **Success: no issues found in 65 source files** |
| `cd apps/web && npm test` (Vitest 4.1.12) | **13 passed** across 3 files |
| `cd apps/web && npm run lint` (ESLint 9 + typescript-eslint + react-hooks) | **0 errors, 0 warnings** |
| `cd apps/web && npm run build` | **tsc clean + Vite production build** (`dist` ≈ 490 kB JS / 146 kB gzip) |
| `npm audit` (web) | **0 vulnerabilities** after upgrading `maplibre-gl` 6.15 and `vitest` 4.1 |
| `alembic upgrade head → downgrade base → upgrade head` on a fresh PostgreSQL DB | **passed** (temporary DB dropped afterwards) |
| API runtime smoke (uvicorn on a fresh DB) | `/health/live` → 200; `/health/ready` → 200 (`database: ok`, `storage: ok`); dev `/openapi.json` → 200 |
| First-admin CLI smoke (fresh DB) | admin created and settings/central account ensured; second run refused with “An administrator already exists” |
| Runtime-only install (fresh venv, no dev deps) | `pip install -r requirements.txt` succeeded; app import + login/refresh smoke passed with an HttpOnly refresh cookie |
| Production/staging config fail-fast | covered by 4 tests in `apps/api/tests/test_config_security.py` |

Environment note: this workstation auto-loads ROS pytest plugins into any pytest invocation, which is why `make test-api` disables plugin autoload. In a clean venv, `.venv/bin/pytest apps/api/tests -q` also works. The test suite is synchronous (Starlette `TestClient`); pytest-asyncio config warnings under the disabled-autoload flag are harmless.

### Manual smoke checklist

1. Sign in as the seeded admin; create a campaign, two sites and a distributor invitation.
2. Record a receipt for central stock, then allocate kg to the distributor.
3. Sign in as the distributor (separately-created account), open **My sites → New delivery update**.
4. Attach a photo, capture location (or submit without it and observe the honest warning), enter a quantity, submit.
5. Back as admin, open **Evidence review**, inspect the private image, then **approve** — the site stock movement is posted and visible in the ledger.
6. Go offline (devtools) as the distributor, save a draft and submit: the draft stays **Queued to sync**, never “Submitted”. Reconnect and retry.

## Configuration notes

- Only `VITE_*` values are shipped to the browser. Never put secrets behind that prefix.
- `VITE_API_BASE_URL` defaults to `/api/v1` (same-origin, works with the Vite proxy and nginx). For a cross-origin SPA, set it at build time and configure `CORS_ALLOWED_ORIGINS` plus cookie settings.
- `VITE_MAP_STYLE_URL` is optional. Empty → the map page renders a coordinate board with real site data; configured → MapLibre loads your public style.
- Evidence storage: `STORAGE_MODE=local` is for development/testing; production requires an S3-compatible bucket (`STORAGE_*`).
- Signed evidence URLs expire (`STORAGE_SIGNED_URL_TTL_SECONDS`, default 120 s).

## Known limitations (honest list)

- **No live map tiles without configuration** — the fallback board is deliberate; nothing is mocked.
- **GPS/EXIF are advisory.** Accuracy, fix age, clock drift, and distance are recorded and flagged; sophisticated spoofing is not detectable by this design.
- **Offline photos** live in IndexedDB and survive reloads in real browsers. In environments without IndexedDB (some test shells), the store falls back to memory — drafts persist in `localStorage`, but attached blobs do not survive a reload.
- **BAG conversions** require an admin-configured `kg_per_bag`; the API rejects bag quantities otherwise.
- **Invitation/reset delivery is not implemented** (see above); tokens are never displayed in the UI.
- **Docker images were not built** in this environment (no Docker daemon); compose/Dockerfile correctness was reviewed but not executed.
- **Single organization** by design; multi-tenancy would require explicit row-level isolation and tests.
- **No screenshot/browser E2E suite**; the web tests cover the critical API-client refresh path, permissions, and the offline submission state machine. Screen layouts were typechecked and built, not browser-automated.

## Documentation index

- [`docs/architecture/API_CONTRACT.md`](docs/architecture/API_CONTRACT.md) — endpoints, enums, error envelope.
- [`docs/architecture/OFFLINE_SYNC.md`](docs/architecture/OFFLINE_SYNC.md) — draft states, idempotency, account switching.
- [`docs/design/SCREEN_SPECS.md`](docs/design/SCREEN_SPECS.md) — screen-by-screen behaviour and copy rules.
- [`docs/design/DESIGN_SYSTEM.md`](docs/design/DESIGN_SYSTEM.md) — tokens, components, accessibility.
- [`docs/ops/ENVIRONMENT_VARIABLES.md`](docs/ops/ENVIRONMENT_VARIABLES.md) — every setting and its security constraints.
- [`docs/ops/IMPLEMENTATION_DECISIONS.md`](docs/ops/IMPLEMENTATION_DECISIONS.md) — decision log, including implementation additions.
- [`handoffs/file_map.md`](handoffs/file_map.md) — per-file ownership, status, and implementation notes.
