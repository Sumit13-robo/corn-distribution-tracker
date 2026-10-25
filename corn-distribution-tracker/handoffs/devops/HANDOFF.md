# DevOps / Release Agent Handoff

## Own
`.env.example`, `Makefile`, production runbook, CI/release workflow if added, observability and backup/restore documentation. Container packaging is retained in the repository but is not part of the supported native workflow.

## Required outcomes
- Reproducible clean-checkout local run with PostgreSQL 17, Django health checks and Vite.
- No secrets in build variables, client bundle, logs or committed files.
- Explicit migration command/job, not every app replica racing migrations.
- TLS/reverse-proxy guidance, strict CORS/CSRF origins, private storage, secure cookies and provider map config.
- Backup and restore instructions include database plus linked evidence objects/versions and a periodic restore drill.
- Readiness/liveness, request ID logging, redaction and metrics/alert guidance.

## Current verification (2026-10-23)
- Native local path verified: Django migrations, 60 backend tests, 23 web tests, production build, 8 Playwright tests, and a live Django + Vite smoke test.
- Gunicorn is pinned/installed; `gunicorn --check-config config.wsgi:application` passes.
- Local Django-schema backup/restore drill passed on synthetic E2E data; production provider drill remains pending.
- `make db-up`/`make dev-up` were removed; `make health` checks the native API probes.
- Container assets are not built or started by the documented workflow.

## Current dev/HTTPS verification (2026-10-25)
- Vite binds to `0.0.0.0` when started with `npm run dev -- --host 0.0.0.0`; `server.allowedHosts` permits `.trycloudflare.com` for a temporary HTTPS quick tunnel. Other hostnames remain subject to Vite's Host check.
- Django `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` include the current tunnel origin in the local `.env` only. The tunnel is public and temporary; use synthetic data, stop it when finished and never treat this as a production ingress.
- The HTTPS phone flow for login and geolocation works. The HTTP LAN URL still works for UI-only checks but cannot access browser geolocation.
- Backend tests are now 61 (raw upload ceiling regression); frontend 34; production build passes. Production still requires a trusted HTTPS reverse proxy and a licenced map/tile provider.

## Delivery-map release check (2026-10-25)

The delivery-only admin map adds no environment variable or migration. It uses the existing admin-only analytics routes and MapLibre/tile configuration; `GET /api/v1/analytics/map-deliveries` returned `401` unauthenticated and `200` with the current admin session in the native dev stack. Current release evidence: backend **67 passed**, web **39 passed across 7 files**, browser E2E **9 passed** (2 setup + 7 workflow, including the admin delivery map), production build passed (app JS 518.10 kB gzip 155.60 kB; existing large-chunk warning). The E2E runner requires ports 8000/5173 to be free because it starts isolated Django/Vite processes with `reuseExistingServer: false`; stop the dev servers before `make test-e2e` and restart them afterwards. The Cloudflare quick tunnel reconnected to the restarted Vite server and returned `200`.

## Report
Exact startup/test/build commands, assumptions about hosting/object storage/map provider, production env requirements and unresolved launch risks.
