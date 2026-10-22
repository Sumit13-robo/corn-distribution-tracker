# Deployment and Operations Runbook

## Environments
Use isolated development, staging and production environments. Each has separate database, object storage bucket, credentials, map provider config and permitted origins. Never use production photos/user records in test fixtures.

## Production topology
- HTTPS reverse proxy / managed ingress.
- Web static assets served over HTTPS.
- FastAPI API behind the same origin path if possible; otherwise strict explicit CORS and credential policy.
- PostgreSQL with PostGIS in a managed/private network, encrypted disks, automated backups and tested restore.
- Private object bucket with public access blocked, encryption, lifecycle/retention rules, access logging policy and short-lived signed URLs.
- Secret manager for DB, session, storage and external provider secrets.
- Central logs/metrics/error reporting with sensitive data redaction.

## Required environment values
See `ops/ENVIRONMENT_VARIABLES.md` and `.env.example`. Production must fail startup if required secrets are missing, default values remain, an insecure cookie mode is selected, CORS is wildcard with credentials, or the storage bucket is public.

## Release sequence
1. Build and scan immutable artifacts; pin dependency lockfiles.
2. Back up database and record current migration revision.
3. Run migrations as a controlled release step; avoid every app replica racing to apply migrations.
4. Deploy API/web and verify health/readiness, authentication, authorized photo URL, test distribution flow and logs.
5. Verify first admin can sign in; confirm invitations, mail provider settings if enabled, map tiles, private storage, and geofence configuration.
6. Perform smoke checks with synthetic test data; check balances reconcile and map/data filters are scoped.
7. Monitor error rates, API latency, upload errors, database pool, pending review queue, rejected uploads and background cleanup jobs.

## Backups and recovery
Document automated backup cadence, encryption, retention, who can restore, RPO/RTO targets chosen by the operator, and restore steps into a separate environment. Restore database and required object versions together where evidence retention depends on both. Perform a periodic restore drill and record results. The concrete procedure and the synthetic restore drill are in [`docs/ops/BACKUP_RESTORE.md`](../ops/BACKUP_RESTORE.md).

## Health and observability
Expose unauthenticated minimal liveness and readiness endpoints without internal secrets; readiness should test dependencies safely. Include request IDs, structured logs, metrics for endpoint latency/errors, DB pool, auth throttles, upload failures, job failures, pending-approval age and ledger reconciliation. Alert on sustained errors or reconciliation mismatch.

## Rollback
Prefer backward-compatible schema migrations. Keep previous web/API artifacts. Define rollback behavior if a migration is destructive; never run an unreviewed down-migration that loses ledger/evidence. Use additive migrations and a separate data-migration step for changes that affect stock history.
