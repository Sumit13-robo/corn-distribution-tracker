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

For the managed Railway (API, PostgreSQL, S3-compatible bucket) plus Vercel (SPA
and same-origin `/api` rewrite) path, use
[`docs/ops/RAILWAY_VERCEL_DEPLOYMENT.md`](../ops/RAILWAY_VERCEL_DEPLOYMENT.md).
The topology and fail-closed checks below still apply.

The bundled nginx configuration listens on HTTP and overwrites `X-Forwarded-For` with `$remote_addr`. If another trusted CDN/ingress sits in front of nginx, configure nginx `real_ip` with the ingress CIDRs or perform the overwrite at that ingress; otherwise every request collapses to the ingress address for audit/rate-limit purposes. Likewise, either terminate TLS in nginx or keep Django `SECURE_SSL_REDIRECT=false` and apply redirect/HSTS at the TLS ingress; do not enable `TRUST_X_FORWARDED_PROTO` on a hop that overwrites the header with `http`.

## Production startup requirements
Django reads settings from the environment (and optionally a local `.env` in development). With `APP_ENV=production`, startup fails fast when:
- `SECRET_KEY` is missing, too short, or still the development sample;
- `ALLOWED_HOSTS` contains `*` (operators must also set the real hostnames);
- session/CSRF cookies are not `Secure`, or SameSite=None is combined with insecure cookies;
- CORS uses a wildcard while credentials are enabled (operators must verify exact origins);
- `STORAGE_MODE` is not `s3` or required storage fields are missing.

Set `TRUST_X_FORWARDED_PROTO=true` only behind a trusted proxy that overwrites `X-Forwarded-Proto`. Set `TRUST_X_FORWARDED_FOR=true` only when the API is unreachable except through a proxy that overwrites `X-Forwarded-For`; the bundled nginx configs always overwrite it with `$remote_addr`. Never expose that trust directly to clients. See `docs/ops/ENVIRONMENT_VARIABLES.md` and `.env.example`.

## Object-storage upload completion
When `STORAGE_MODE=s3`, the browser PUTs directly to the private bucket using a short-lived presigned URL. The application principal needs `s3:HeadBucket` for readiness, `s3:GetObject`/`s3:HeadObject` for completion and viewing, and `s3:PutObject` for the presigned upload/verification path (scope these to the evidence prefix). The bucket must have a CORS rule allowing the SPA origin, `PUT`, and the headers returned by the upload-intent response (`Content-Type`, plus `x-amz-server-side-encryption` and, for SSE-KMS, `x-amz-server-side-encryption-aws-kms-key-id` when configured). It must not allow public reads. After the PUT, the SPA calls `POST /api/v1/evidence/upload-intents/{id}/complete`; the API reads the object with its private credentials, decodes the image, enforces size/pixel limits, records the SHA-256 digest and only then permits attachment. Reads are bounded and private blob reads re-check the recorded hash. A delivery submission also performs this check lazily if the completion call was lost. Bucket lifecycle rules should delete unbound objects after a short retention window. Verify the exact CORS headers against a real bucket before launch because a header mismatch makes the browser PUT fail at the preflight/signature check. The repository's simulated S3 probe is not a substitute for that provider check.

## Release sequence
1. Build and scan immutable artifacts; pin dependency lockfiles. CI runs Ruff, mypy, migration drift checks, API tests, web lint/typecheck/unit tests, `npm audit`, a production web build and the Playwright E2E suite on every push. CI is not a substitute for staging acceptance.
2. Back up the database and record applied Django migrations (`python manage.py showmigrations`).
3. Run `python manage.py migrate --noinput` as a controlled release step. Do not let every Gunicorn worker race to migrate; migrate once before starting replicas. Migration `0004` temporarily drops the append-only stock trigger to backfill legacy idempotency scopes and recreates it in the same transactional migration. Existing idempotency keys have no payload fingerprint and now fail closed; drain or re-key any offline clients holding a pre-upgrade key.
4. Start Gunicorn against `config.wsgi:application` and verify `/health/live` plus `/health/ready`. Readiness reports `503` if the database or configured evidence storage is unavailable.
5. Verify sign-in, an authorized evidence URL, an admin mutation with CSRF, and the distributor submission/review flow using synthetic data. For S3, verify the complete-upload call rejects a missing or replaced object.
6. Confirm balances reconcile (`net_external_kg == sum_account_balances_kg`), role scoping is enforced, and the bundle contains no secrets.
7. Monitor error rates, latency, upload completion failures, database connections, pending review age and ledger reconciliation.

## Health and observability
- Liveness: `GET /health/live` (also available under `/api/v1`).
- Readiness: `GET /health/ready` probes the database and configured evidence storage without exposing secrets.
- Requests carry sanitized `X-Request-ID` values and structured method/path/status/duration logs.
- There is no bundled APM or metrics exporter; connect the logs and health endpoints to the operator's monitoring platform.
- Rate limits are process-local in this build and the in-memory bucket table is capped to bound memory. A multi-replica deployment must still move counters to a shared store such as Redis; otherwise each worker enforces its own limit.
- The application can emit HSTS and redirect HTTP to HTTPS through `SECURE_HSTS_SECONDS`/`SECURE_SSL_REDIRECT` when it owns the outer hop. If TLS terminates at an ingress, configure the equivalent policy there and record the evidence.

## Backups and recovery
Document automated backup cadence, encryption, retention, who can restore, RPO/RTO targets, and restore steps into a separate environment. Restore the database and required object versions together where evidence retention depends on both. The concrete procedure and synthetic restore drill are in [`docs/ops/BACKUP_RESTORE.md`](../ops/BACKUP_RESTORE.md).

## Rollback
Prefer backward-compatible additive schema migrations. Keep the previous web/API artifacts. Never run an unreviewed down-migration that loses ledger or evidence rows. Django migration history lives in `django_migrations`; the append-only database triggers intentionally make ledger/audit deletion fail. Roll back application code first, then use a separately reviewed data-migration plan if the schema must change.
