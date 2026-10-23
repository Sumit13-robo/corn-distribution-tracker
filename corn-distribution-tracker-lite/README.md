# Corn Distribution Tracker — Lite edition

A deliberately small second edition of the Corn Distribution Tracker lives in
this folder. It preserves the same core workflow and visual language as the full
React + DRF app in [`../corn-distribution-tracker`](../corn-distribution-tracker),
but runs as a plain server-rendered Django application.

- Full edition: <http://localhost:5173> (Vite) with the API at <http://localhost:8000>.
- Lite edition: <http://127.0.0.1:8001> (Django templates only).
- The two apps are separate deployments with separate databases and settings.
  The Lite edition does not modify or replace the full edition.

## What the Lite edition does

Central stock receipt → distributor allocation → delivery submission → admin
review → approved delivery posts distributor stock to the site.

Two roles:

- **Administrator**: campaigns, sites, distributor accounts, assignments, stock
  receipts, allocations, review queue, inventory ledger, activity feed.
- **Distributor**: own stock and target progress, active assignments, delivery
  submission with optional private photo evidence, own delivery history.

Every stock change is a `StockMovement` row. Account balances are derived from
those rows rather than cached, so the visible ledger and the balances cannot
drift apart. A submitted delivery reserves its quantity; approval moves it from
the distributor account to the site account; rejection releases the reservation
without changing balances.

## Why this edition is smaller

- Server-rendered Django templates, no React, no build step, no API layer.
- Django auth, sessions and CSRF; no token or invitation infrastructure.
- SQLite database; no PostgreSQL, Docker or object storage required.
- One Django process and two static assets (`lite.css`, `app.js`).
- Django's built-in admin is available at `/django-admin/` for emergency account
  and data inspection. The main UI remains the server-rendered app.

## Quick start

Requires Python 3.12+ and the packages in `requirements.txt` (Django 5.2 and
Pillow for evidence-image validation).

```bash
cd corn-distribution-tracker-lite
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_demo
python manage.py runserver 127.0.0.1:8001
```

Open <http://127.0.0.1:8001/> and sign in with the credentials printed by
`seed_demo`. The command generates random one-time passwords when the environment
variables below are absent, and prints them once to the terminal:

```bash
LITE_ADMIN_PASSWORD='choose-a-strong-password' \
LITE_AMINA_PASSWORD='choose-a-strong-password' \
LITE_JOHN_PASSWORD='choose-a-strong-password' \
python manage.py seed_demo
```

The command is idempotent. It never resets an existing account's password and
does not print existing passwords. To reset one later:

```bash
python manage.py changepassword admin@example.org
# or use Django admin → Users
```

Passwords are never hardcoded in source, templates, fixtures or README files.
Do not use the seed command against a production database.

The workspace already contains the full app's virtual environment. To run the
Lite edition without creating another one:

```bash
../corn-distribution-tracker/.venv/bin/python manage.py migrate
../corn-distribution-tracker/.venv/bin/python manage.py seed_demo
../corn-distribution-tracker/.venv/bin/python manage.py runserver 127.0.0.1:8001
```

## Walkthrough

1. Sign in as the administrator.
2. **Inventory → Record receipt** to add central stock, then **Allocate stock**
   to a distributor. Balances are shown before and after.
3. Create a **campaign**, a **site** and a **distributor** under **People**, then
   connect them under **Assignments** with a kilogram target.
4. Sign in as the distributor. The dashboard shows held stock, reserved stock,
   available stock and target progress. **Submit delivery** for an active
   assignment, optionally attaching a JPEG/PNG/WebP photo.
5. Sign in as the administrator again. The pending item appears in the review
   queue. Open it, inspect the private photo if present, and approve or reject.
6. Approval posts the quantity to the site; rejection keeps the record and
   releases the reservation. Check **Inventory** and **Activity** for the result.

## Routes

| Route | Who | Purpose |
| --- | --- | --- |
| `/login/`, `/logout/` | Public / signed in | Session sign-in and POST-only sign-out |
| `/` | Both roles | Role-specific dashboard |
| `/campaigns/`, `/sites/`, `/people/`, `/assignments/` | Admin | Setup and assignment planning |
| `/inventory/` | Admin | Central, distributor and site balances plus ledger |
| `/inventory/receipt/`, `/inventory/allocation/` | Admin | Post stock receipts and allocations |
| `/deliveries/` | Both roles, scoped | Delivery history and review queue |
| `/deliveries/new/` | Distributor | Submit a delivery |
| `/deliveries/<id>/` | Owner or admin | Detail, evidence and review outcome |
| `/deliveries/<id>/review/` | Admin, POST | Approve or reject |
| `/deliveries/<id>/photo/` | Owner or admin | Authenticated private evidence view |
| `/activity/` | Admin | Audit-style activity feed |
| `/django-admin/` | Staff | Optional operator surface |

## Security and integrity choices

- Authorization is server-side. Every admin route checks the admin role; every
  distributor query is scoped to the signed-in account. UI links are not a
  permission boundary.
- Login attempts are throttled per client IP; successful sign-ins clear prior
  failures. `X-Forwarded-For` is ignored unless `DJANGO_USE_X_FORWARDED_FOR=1` is
  explicitly enabled behind a trusted proxy.
- CSRF protection is enabled for every POST form; sign-out is POST-only.
- Quantities are `Decimal(12,3)` kilograms, not floats. Model forms enforce the
  same precision and positive quantities.
- Stock changes run through `tracker/services.py` inside database transactions.
  `select_for_update()` is used at the documented lock points. SQLite serialises
  writes on this single-node deployment, but its `select_for_update()` is a no-op
  at the SQL level.
- The stock ledger is append-only through the product and the Django admin
  configuration. Ledger and delivery records are read-only in the admin.
- Evidence is stored under `MEDIA_ROOT` and is **not** exposed through
  `MEDIA_URL`. It is served only by the authenticated `delivery_photo` view to
  the owning distributor or an administrator, with `Cache-Control: private,
  no-store`. Uploads are validated as real images by Pillow, restricted to
  JPEG/PNG/WebP and capped at 5 MB.
- Production startup refuses to run with the development/short secret or a
  wildcard host when `DJANGO_DEBUG=0`. Secure cookies, HTTPS redirect and
  optional HSTS settings are applied in that mode.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `DJANGO_DEBUG` | `1` | Set to `0` for production behavior. |
| `DJANGO_SECRET_KEY` | dev-only value | Required when `DJANGO_DEBUG=0`. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated explicit hosts; `*` is rejected in production. |
| `DJANGO_USE_X_FORWARDED_FOR` | `0` | Trust the proxy header only when a stripping proxy is in front. |
| `DJANGO_SECURE_SSL_REDIRECT` | `1` when `DEBUG=0` | HTTPS redirect. |
| `DJANGO_SECURE_HSTS_SECONDS` | `0` | Set after confirming HTTPS-only service; e.g. `31536000`. |
| `LITE_ADMIN_PASSWORD` | generated | One-time seed password. |
| `LITE_AMINA_PASSWORD` | generated | One-time seed password. |
| `LITE_JOHN_PASSWORD` | generated | One-time seed password. |

The Lite edition has no frontend build and no `VITE_` configuration. Only public
configuration belongs in frontend variables in the full edition; secrets must
never be exposed to a browser.

## Tests and checks (verified on this host)

Django `manage.py` commands use the project environment. The following were run
against this folder on 2026-10-23:

```bash
python manage.py check
python manage.py test tracker -v 1
ruff check .
```

Results:

- `33` Django tests pass, covering role access, ownership scoping, login
  throttling, receipt/allocation balances, reservation and double-spend
  prevention, inactive assignment/campaign/site guards, approval posting,
  rejection release, private photo access, form validation, seeded demo data
  idempotency and template rendering.
- `manage.py check` reports no issues.
- `ruff check .` passes.
- Manual browser checks were completed at 1440 px and 360 px widths (dashboard,
  review detail, deliveries list, mobile navigation), including a distributor
  submission with private photo evidence and administrator approval. No Docker
  runtime was available on this host, so no Docker image or Compose stack was
  verified.
- Production fail-fast was checked manually: `DJANGO_DEBUG=0` without a secret,
  with a short secret, and with a wildcard host each fails; a valid explicit
  configuration passes `manage.py check`.

## Deliberate limitations

The Lite edition is intentionally not feature-equivalent to the full app. It
omits, among other things:

- Invitation emails, self-service password reset, and password-change screens.
  Administrators reset passwords through Django admin or `changepassword`.
- GPS capture, maps, distance flags and geospatial review.
- Offline drafts, sync queues and duplicate-submit idempotency keys.
- Analytics, CSV export, pagination and bulk import.
- S3/object-storage evidence, thumbnails/signed short-lived URLs, and EXIF
  stripping. Stored evidence is private and access-controlled, but the original
  file (including any metadata) is kept as uploaded. GPS metadata is not treated
  as proof.
- Append-only database triggers. The app and admin never edit ledger rows, but a
  database administrator could still modify the SQLite file directly.
- A shared cache or distributed rate limiter. The login throttle is process-local.
- Background jobs, email transport, Docker packaging and production process
  supervision.

If those behaviors are required, use the full edition in
[`../corn-distribution-tracker`](../corn-distribution-tracker).

## Production notes

- Serve through HTTPS with a reverse proxy so the secure-cookie and redirect
  settings work as intended.
- Set a long random `DJANGO_SECRET_KEY`, explicit `DJANGO_ALLOWED_HOSTS`,
  `DJANGO_DEBUG=0`, and `DJANGO_USE_X_FORWARDED_FOR=1` only if the proxy strips
  client-supplied forwarding headers.
- Run `python manage.py migrate --noinput` and
  `python manage.py collectstatic --noinput`.
- Back up both `db.sqlite3` and `media/` together, and keep `media/` outside any
  public static path. Never expose it through nginx or another web server.
- SQLite is appropriate for a small single-node deployment. A multi-process or
  multi-node deployment needs a real database, a shared cache for throttling, and
  a production-hardening review of ledger immutability and evidence storage.

## Relationship to the full edition

The full edition remains at [`../corn-distribution-tracker`](../corn-distribution-tracker)
with its own README, tests and Docker configuration. This folder is additive and
shares the design language: forest green surfaces, maize accents, warm neutral
backgrounds, the same card/table patterns and the same mobile-first layout
principles. All demo names, emails, addresses, stock and photos are synthetic.
