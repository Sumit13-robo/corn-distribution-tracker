# Backup, Restore and Evidence Retention

This is the operator procedure for a production-like deployment. It complements the
[deployment runbook](../architecture/DEPLOYMENT_RUNBOOK.md). Practice on synthetic data first; never
restore a backup over a live database without an explicit incident/release decision.

## Backup scope

Back up these as one recoverable set:

1. **PostgreSQL** — the source of truth for users, stock movements, distributions, reservations, audit
   events and evidence metadata. The Alembic revision (`alembic_version.version_num`) is in the same dump.
2. **Evidence object storage** — the private S3-compatible bucket, or the local `LOCAL_STORAGE_DIR` in
   development. Preserve object keys exactly; evidence rows reference them.
3. **Configuration and secrets** — kept in the secret manager, not in the repository or the database dump.
   Record the non-secret configuration version used for the restore.

Database rows and evidence objects must be captured in the same operational window. A database restore
whose photo keys point at missing or newer objects is not a complete restore.

## Recovery objectives

The operator must record, before go-live:

- **RPO** (acceptable data loss window) and backup frequency.
- **RTO** (acceptable restore time).
- Retention for database backups and evidence versions.
- Who can approve a restore and who has access to encryption keys.
- The legal/retention policy for evidence and whether legal hold applies.

The application does not implement automatic retention deletion or a backup scheduler; use managed
database backups and bucket versioning/lifecycle rules, or an equivalent controlled job.

## PostgreSQL backup

Convert the SQLAlchemy driver URL to a `pg_dump`-compatible URL (do not put real credentials in shell
history; use your secret manager or a protected environment file):

```bash
export PG_URL="${DATABASE_URL/postgresql+psycopg:/postgresql:}"
export BACKUP_FILE="corn-tracker-$(date -u +%Y%m%dT%H%M%SZ).dump"

pg_dump \
  --format=custom \
  --no-owner \
  --no-privileges \
  --file="$BACKUP_FILE" \
  "$PG_URL"

sha256sum "$BACKUP_FILE" > "$BACKUP_FILE.sha256"
```

Store the dump and checksum encrypted in a separate failure domain. Keep the corresponding evidence
object versions for at least the same retention period.

## Evidence backup

### S3-compatible storage

Use the provider's native versioning/replication or a server-side copy; do not download originals to an
unencrypted workstation. Example with AWS CLI against a private bucket:

```bash
aws s3 sync "s3://$STORAGE_BUCKET" "s3://$BACKUP_BUCKET/evidence-$(date -u +%Y%m%dT%H%M%SZ)/" \
  --only-show-errors
```

Record the bucket version ids or object manifest. Restore objects to a **private** bucket, retaining the
same keys, and verify bucket public-access blocking before starting the API.

### Local development storage

```bash
tar -C "$LOCAL_STORAGE_DIR" -czf "evidence-$(date -u +%Y%m%dT%H%M%SZ).tar.gz" .
```

Local mode is for development/testing only. Production startup rejects it.

## Restore procedure

1. Provision an isolated target database and private bucket. Do not reuse production endpoints.
2. Create the database (name it clearly; for a drill use a name containing `restore` or `e2e`):

   ```bash
   createdb corn_tracker_restore
   pg_restore --no-owner --no-privileges --dbname=corn_tracker_restore "$BACKUP_FILE"
   ```

3. Restore evidence objects into the configured bucket/path **before** running the readiness check.
4. Start the API with the target `DATABASE_URL`, storage settings, and a non-production `SECRET_KEY`.
5. Verify:
   - `alembic current` reports the expected revision;
   - `/health/ready` returns 200 with `database: ok` and `storage: ok`;
   - row counts for users, distribution records, stock movements, photo evidence and audit events match
     the source snapshot;
   - every `photo_evidence.storage_key` exists in the restored storage (see drill query below);
   - API read paths work and the app can issue a short-lived evidence view URL.
6. Run the synthetic smoke flow (admin login, site/campaign, distributor submission, approval) before
   switching traffic.
7. Record the restore result, duration, operator and any reconciliation exceptions.

## Restore verification query

```bash
psql -d corn_tracker_restore -Atc \
  "select storage_key from photo_evidence" |
while IFS= read -r key; do
  test -n "$key" || continue
  test -f "${LOCAL_STORAGE_DIR%/}/$key" ||
    echo "MISSING evidence object: $key" >&2
done
```

For S3, replace the file test with `aws s3api head-object --bucket "$STORAGE_BUCKET" --key "$key"`.

## Rollback

Prefer backward-compatible migrations and keep the previous API/web artifacts. Do not run a destructive
down-migration as a rollback shortcut. Restore the database and evidence set together, then verify the
ledger reconciliation endpoint and audit trail before reopening traffic.

## Tested local drill (2026-10-22)

A drill was run against the synthetic `corn_tracker_e2e` database (not production data):

- `pg_dump --format=custom` produced a 61,116-byte dump.
- Restored into isolated `corn_tracker_restore_e2e`.
- Source and restored Alembic revision: `0001`.
- Row counts matched: users 2/2, distribution records 2/2, stock movements 3/3, photo evidence 2/2,
  audit events 21/21.
- Both referenced evidence objects were present under the local synthetic storage directory.
- The drill database was dropped after verification.

This proves the local PostgreSQL dump/restore procedure; it does not substitute for a restore drill against
the production database/storage provider, which requires operator credentials and a maintenance window.
