# Integration Checklist

> **Completion status (2026-10-22):** All build/integration items below were implemented and verified on the
> non-Docker path (46 backend tests, 14 frontend tests, 8 Playwright E2E tests, lint/typecheck/build, migration,
> and a synthetic PostgreSQL restore drill). Docker/PostGIS runtime startup could not be executed on this host
> (no Docker/Podman daemon; rootless namespaces blocked); see the README for that limitation and the production
> launch risks (MFA, malware scanning, APM/alerting, email delivery).

## Foundation
- [x] Confirm existing repository and preserve working files.
- [x] Create app folders and safe `.env.example`.
- [x] Local PostgreSQL and local object-storage adapter boot (the Compose image includes PostGIS, but the schema does not require spatial types).
- [x] Health endpoints and request IDs.
- [x] First Alembic migration runs on empty DB.

## Security
- [x] Login/refresh/logout, reset/invite token expiry and admin bootstrap.
- [x] Role/ownership checks per endpoint; IDOR tests.
- [x] Private uploads, upload size/type controls, expiring signed URLs.
- [x] Rate limits, safe errors, secret redaction, strict CORS/cookies.

## Domain
- [x] Campaigns/sites/assignments.
- [x] Inventory receipt/allocation/adjustment ledger.
- [x] Distributor delivery reservation and submit.
- [x] Geo validation and image hash/metadata flags.
- [x] Admin review; atomic approval movement; rejection releases reservation.
- [x] Analytics formulas/audit/export.

## Frontend
- [x] Login + role-aware routing and session expiry.
- [x] Admin overview/map/sites/distributors/inventory/review/analytics.
- [x] Distributor overview/sites/delivery/photo/location/history/offline drafts.
- [x] Real API data only; all errors and permission states handled.
- [x] Responsive/mobile checks automated at 360 px; semantic HTML, labels, focus styles and reduced-motion support are implemented (a formal assistive-technology audit remains operator QA).

## Release
- [x] Backend/frontend tests, lint, type checks and production builds.
- [x] Stock concurrency/idempotency test and reconciliation.
- [x] Privacy/security review and no secrets in client bundle.
- [x] Backup/restore and deployment runbook reviewed; local synthetic DB/evidence restore drill passed.
- [x] File map statuses and final report accurate.
