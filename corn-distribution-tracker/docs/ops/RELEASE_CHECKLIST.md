# Release Checklist

> **Status:** This is the operator checklist for a real staging/production deployment, not a claim that one has
> happened. Repository-level tests, lint/type checks, build, migrations and a synthetic local restore drill are
> recorded in the README; Docker runtime verification and all environment/operator items below remain to be completed
> on the target platform. See [`BACKUP_RESTORE.md`](BACKUP_RESTORE.md) for the database/evidence procedure.

## Before deployment
- [ ] Review PRs and file handoff completion; no critical TODOs or hardcoded credentials.
- [ ] Lockfiles committed; dependency scan/license policy reviewed.
- [ ] Format, lint, type check, backend/frontend tests and production builds pass.
- [ ] Security/authorization tests include changing IDs and calling restricted endpoints directly.
- [ ] Ledger concurrency/idempotency tests pass; balances reconcile after sample lifecycle.
- [ ] Evidence upload, private view URL expiration, invalid MIME/size rejection and geo flags tested.
- [ ] Responsive and accessibility smoke checks run on desktop/mobile widths.
- [ ] No test seed/demo data enabled in production.

## Environment and data
- [ ] Secret manager values configured and rotated from development.
- [ ] Database available privately; migration backup captured; migration applied by controlled job.
- [ ] Object bucket is private, encrypted and lifecycle/retention rules reviewed.
- [ ] TLS/HTTPS, strict origins/CORS, secure cookies and trusted proxy config verified.
- [ ] Map provider production terms/quotas/domain restrictions checked.
- [ ] First admin provisioned securely; admin MFA status assessed/documented.
- [ ] At least one test distributor, campaign, site, inventory receipt and allocation created using synthetic data in staging.

## Smoke test
- [ ] Login/logout/refresh and session expiry work.
- [ ] Admin creates a site/campaign/allocation.
- [ ] Distributor sees only assigned sites and can submit one test delivery with evidence.
- [ ] Admin reviews evidence and approves; exactly one ledger movement is created.
- [ ] Rejected submission releases reservation without changing ledger balance.
- [ ] Map and analytics reflect approved vs pending quantities correctly.
- [ ] Photo view URL is private, authorized and expires.
- [ ] Logs include request IDs but not tokens, signed URLs or private content.

## Operations
- [ ] Dashboards/alerts configured for API failure, upload failure, queue age, storage errors, DB saturation and ledger mismatch.
- [ ] Backup/restore procedure tested and evidence object retention reconciled.
- [ ] Rollback artifact and schema rollback/forward plan documented.
- [ ] Support owner, incident contact and retention/contact policy documented.
- [ ] Any missing MFA, malware scanning, email delivery, offline media limitations or monitoring integrations explicitly listed as launch risks.
