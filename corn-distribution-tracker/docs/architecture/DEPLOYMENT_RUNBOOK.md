# Deployment and Operations Runbook

## Environments
Use isolated development, staging and production environments. Each has a separate database, object storage bucket, credentials, map provider config and permitted origins. Never use production photos or user records in test fixtures.

## Production topology
- HTTPS reverse proxy or managed ingress.
- Static SPA assets served over HTTPS.
- Django/DRF API behind the same origin path where possible; otherwise use explicit CORS origins with credentials and a matching `CSRF_TRUSTED_ORIGINS` entry.
- PostgreSQL in a managed/private network, encrypted disks, automated backups and tested restore. PostGIS is not required by this schema.
- Private object bucket with public access blocked, encryption, lifecycle/retention rules, access logging and short-lived signed URLs.
- Secret manager for database, Django `SECRET_KEY`, storage and external provider secrets.
- Central logs/metrics/error reporting with sensitive data redaction.

## Production startup requirements
Django reads settings from the environment (and optionally a local `.env` in development). With `APP_ENV=production`, startup fails fast when:
- `SECRET_KEY` is missing, too short, or still the development sample;
- `ALLOWED_HOSTS` contains `*` (operators must also set the real hostnames);
- session/CSRF cookies are not `Secure`, or SameSite=None is combined with insecure cookies;
- CORS uses a wildcard while credentials are enabled (operators must verify exact origins);
- `STORAGE_MODE` is not `s3` or required storage fields are missing.

Set `TRUST_X_FORWARDED_PROTO=true` only behind a trusted proxy that overwrites `X-Forwarded-Proto`; never expose that trust directly to clients. See `ops/ENVIRONMENT_VARIABLES.md` and `.env.example`.

## Release sequence
1. Build and scan immutable artifacts; pin dependency lockfiles.
2. Back up the database and record applied Django migrations (`python manage.py showmigrations`).
3. Run `python manage.py migrate --noinput` as a controlled release step. Do not let every Gunicorn worker race to migrate; migrate once before starting replicas.
4. Start Gunicorn against `config.wsgi:application` and verify `/health/live` plus `/health/ready`.
5. Verify sign-in, an authorized evidence URL, an admin mutation with CSRF, and the distributor submission/review flow using synthetic data.
6. Confirm balances reconcile, role scoping is enforced, and the bundle contains no secrets.
7. Monitor error rates, latency, upload failures, database connections, pending review age and ledger reconciliation.

## Health and observability
- Liveness: `GET /health/live` (also available under `/api/v1`).
- Readiness: `GET /health/ready` probes the database and configured evidence storage without exposing secrets.
- Requests carry sanitized `X-Request-ID` values and structured method/path/status/duration logs.
- There is no bundled APM or metrics exporter; connect the logs and health endpoints to the operator's monitoring platform.
- Rate limits are process-local in this build. A multi-replica deployment should move counters to a shared store such as Redis.

## Backups and recovery
Document automated backup cadence, encryption, retention, who can restore, RPO/RTO targets, and restore steps into a separate environment. Restore the database and required object versions together where evidence retention depends on both. The concrete procedure and synthetic restore drill are in [`docs/ops/BACKUP_RESTORE.md`](../ops/BACKUP_RESTORE.md).

## Rollback
Prefer backward-compatible additive schema migrations. Keep the previous web/API artifacts. Never run an unreviewed down-migration that loses ledger or evidence rows. Django migration history lives in `django_migrations`; the append-only database triggers intentionally make ledger/audit deletion fail. Roll back application code first, then use a separately reviewed data-migration plan if the schema must change.
