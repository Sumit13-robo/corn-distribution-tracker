# Integration Checklist

> **Completion status (2026-10-22):** Implemented and verified on the non-Docker path
> (58 backend tests, 18 frontend tests, 8 Playwright E2E tests, lint/typecheck/build, Django
> migrations, 360 px audit, synthetic restore drill). Docker runtime remains pending on a Docker-capable
> host; see the README for limitations and production launch risks (MFA, malware scanning, APM/alerting,
> email delivery).

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
- [x] Campaigns/sites/assignments.
- [x] Inventory receipt/allocation/adjustment ledger with append-only triggers.
- [x] Distributor delivery reservation and submit.
- [x] Geo validation and image hash/metadata flags.
- [x] Admin review; atomic approval movement; rejection releases reservation.
- [x] Analytics formulas/audit/export.

## Frontend
- [x] Login + role-aware routing and session expiry.
- [x] Admin overview/map/sites/distributors/inventory/review/analytics/settings/audit.
- [x] Distributor overview/sites/delivery/photo/location/history/offline drafts/drafts-sync.
- [x] Real API data only; all errors and permission states handled.
- [x] Responsive/mobile checks automated at 360 px; semantic HTML, labels, focus styles and reduced-motion support are implemented (a formal assistive-technology audit remains operator QA).

## Release
- [x] Backend/frontend tests, lint, type checks and production builds.
- [x] Stock concurrency/idempotency test and reconciliation.
- [x] Privacy/security review and no secrets in client bundle.
- [x] Backup/restore drill rerun against the synthetic Django schema; counts and evidence objects matched.
- [x] File map statuses and final report accurate.
- [ ] Docker image build and Compose startup on a Docker-capable host.
