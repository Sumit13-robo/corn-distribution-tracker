# Integration Checklist

> **Completion status (2026-10-25):** Implemented and verified on the native path
> (66 backend tests, 37 frontend tests, 8 Playwright E2E tests, lint/typecheck/build, Django
> migrations including campaign-scoped name-only sites, native live smoke, 360 px audit, synthetic
> restore drill, location-warning removal and scoped development-data cleanup). See the README for
> limitations and production launch risks (MFA, malware scanning, APM/alerting, email delivery,
> deferred map/review enhancements).

## Foundation
- [x] Confirm existing repository and preserve working files.
- [x] Create app folders and safe `.env.example`.
- [x] Local PostgreSQL and local object-storage adapter boot (no PostGIS dependency).
- [x] Health endpoints and request IDs.
- [x] Django migrations run on an empty database.

## Security
- [x] Login/logout/session restore, CSRF, reset/invite token expiry and admin bootstrap.
- [x] Role/ownership checks per endpoint; IDOR tests.
- [x] Private uploads, upload size/type controls, expiring signed URLs.
- [x] Rate limits, safe errors, secret redaction, strict CORS/cookies and production fail-fast settings.

## Domain
- [x] Campaigns/sites/assignments, including campaign-scoped name-only sites with optional location added later.
- [x] Inventory receipt/allocation/adjustment ledger with append-only triggers.
- [x] Distributor delivery reservation and submit.
- [x] Non-blocking location capture and non-location evidence-integrity flags (duplicate hash, capture-time drift, unexpected type).
- [x] Admin review; atomic approval movement; rejection releases reservation.
- [x] Analytics formulas/audit/export.

## Frontend
- [x] Login + role-aware routing and session expiry.
- [x] Admin overview/map/campaigns-with-sites/distributors/inventory/review/analytics/settings/audit.
- [x] Distributor overview/sites/delivery/photo/location/history/offline drafts/drafts-sync.
- [x] Real API data only; all errors and permission states handled.
- [x] Responsive/mobile checks automated at 360 px; semantic HTML, labels, focus styles and reduced-motion support are implemented (a formal assistive-technology audit remains operator QA).

## Release
- [x] Backend/frontend tests, lint, type checks and production builds.
- [x] Stock concurrency/idempotency test and reconciliation.
- [x] Privacy/security review and no secrets in client bundle.
- [x] Backup/restore drill rerun against the synthetic Django schema; counts and evidence objects matched.
- [x] Native Django + Vite smoke test on the local PostgreSQL database.
- [x] Development data reduced to Kolhapur + retained 1 kg record + minimum ledger chain + all logins, after database/private-storage backup.
- [x] File map statuses and final report accurate.
