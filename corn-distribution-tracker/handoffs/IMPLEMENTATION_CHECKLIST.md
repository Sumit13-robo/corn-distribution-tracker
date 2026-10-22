# Integration Checklist

## Foundation
- [ ] Confirm existing repository and preserve working files.
- [ ] Create app folders and safe `.env.example`.
- [ ] Local DB/PostGIS and object storage adapter boot.
- [ ] Health endpoints and request IDs.
- [ ] First Alembic migration runs on empty DB.

## Security
- [ ] Login/refresh/logout, reset/invite token expiry and admin bootstrap.
- [ ] Role/ownership checks per endpoint; IDOR tests.
- [ ] Private uploads, upload size/type controls, expiring signed URLs.
- [ ] Rate limits, safe errors, secret redaction, strict CORS/cookies.

## Domain
- [ ] Campaigns/sites/assignments.
- [ ] Inventory receipt/allocation/adjustment ledger.
- [ ] Distributor delivery reservation and submit.
- [ ] Geo validation and image hash/metadata flags.
- [ ] Admin review; atomic approval movement; rejection releases reservation.
- [ ] Analytics formulas/audit/export.

## Frontend
- [ ] Login + role-aware routing and session expiry.
- [ ] Admin overview/map/sites/distributors/inventory/review/analytics.
- [ ] Distributor overview/sites/delivery/photo/location/history/offline drafts.
- [ ] Real API data only; all errors and permission states handled.
- [ ] Responsive/mobile/accessibility checks.

## Release
- [ ] Backend/frontend tests, lint, type checks and production builds.
- [ ] Stock concurrency/idempotency test and reconciliation.
- [ ] Privacy/security review and no secrets in client bundle.
- [ ] Backup/restore and deployment runbook reviewed.
- [ ] File map statuses and final report accurate.
