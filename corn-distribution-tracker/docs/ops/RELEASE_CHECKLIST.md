# Release Checklist

> **Status:** This is the operator checklist for a real staging/production deployment, not a claim that one has
> happened. Repository-level tests, lint/type checks, build, migrations, native local smoke, a simulated
> S3-compatible evidence drill and a synthetic local restore drill through schema `0004` are recorded in the
> README; all environment/operator items below remain to be completed on the target platform. See
> [`BACKUP_RESTORE.md`](BACKUP_RESTORE.md) for the database/evidence procedure.

## Before deployment
- [ ] Review PRs and file handoff completion; no critical TODOs or hardcoded credentials.
- [ ] Lockfiles committed; dependency scan/license policy reviewed; the CI `npm audit` and dependency-review jobs are green on the release commit.
- [ ] Format, lint, type check, backend/frontend tests, Playwright E2E and production builds pass; `make check` is green locally.
- [ ] Security/authorization tests include changing IDs and calling restricted endpoints directly.
- [ ] Ledger concurrency/idempotency tests pass; same-key retries replay, different payloads conflict, legacy keys fail closed, and balances reconcile after sample lifecycle.
- [ ] Evidence upload, private view URL expiration, invalid MIME/size rejection, same-size and oversized replacement rejection, and non-location evidence-integrity flags tested. Location capture must not gate approval.
- [ ] Responsive and accessibility smoke checks run on desktop/mobile widths.
- [ ] No test seed/demo data enabled in production.

## Environment and data
- [ ] Secret manager values configured and rotated from development.
- [ ] Database available privately; migration backup captured; migration applied by controlled job. For `0004`, verify legacy stock-movement idempotency keys were backfilled and retain the pre-migration backup.
- [ ] Object bucket is private, encrypted and lifecycle/retention rules reviewed. CORS allows the SPA origin, `PUT`, `Content-Type` and any configured `x-amz-server-side-encryption*` headers; public reads are blocked.
- [ ] Direct-upload completion (`POST /evidence/upload-intents/{id}/complete`) succeeds against the real bucket, and a replaced/missing object is rejected before attachment.
- [ ] TLS/HTTPS, strict origins/CORS, secure cookies, HSTS/redirect policy, CSP/COOP headers and trusted proxy config verified at the actual ingress. `TRUST_X_FORWARDED_FOR` is enabled only when the API is unreachable except through a proxy that overwrites the header.
- [ ] Multi-worker rate limiting is backed by a shared store, or the deployment is explicitly constrained to one process; the process-local bucket table is memory-bounded but not shared.
- [ ] Map provider production terms/quotas/domain restrictions checked.
- [ ] First admin provisioned securely; admin MFA status assessed/documented.
- [ ] At least one test distributor, campaign, site, inventory receipt and allocation created using synthetic data in staging.

## Smoke test
- [ ] Login/logout/session expiry and CSRF-protected mutations work.
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
