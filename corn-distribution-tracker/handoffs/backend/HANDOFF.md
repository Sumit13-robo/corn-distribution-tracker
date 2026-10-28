# Backend Agent Handoff

## Own
`apps/api/**`: Django/DRF configuration, models/migrations, serializers, views, services, management commands and backend tests. Coordinate endpoint/schema changes with the lead before changing contracts.

## Sequence
1. Settings + PostgreSQL ORM + health endpoints.
2. Models and Django migrations; verify append-only triggers on a clean database.
3. Session/CSRF auth, RBAC and controlled admin bootstrap command.
4. Campaigns/sites/assignments and account setup.
5. Inventory ledger and concurrency protection.
6. Evidence storage + geo validation + submission/approval/rejection.
7. Analytics/export/audit, tests and API contract review.

## Hard gates
- Do not add a “current stock” mutable field as truth.
- Submit reservation and approval operations must be race-safe.
- Approval must atomically post one movement and audit event.
- All data queries are scoped by role/ownership on the server.
- A distributor never chooses the `reviewed_by` user; derive it from the session.
- Private storage and short-lived signed URLs only.
- Do not return EXIF/coordinates for records the caller cannot access.
- Never log raw invitation/reset tokens or session/CSRF secrets.

## Report
List migration commands/results, route list, tests run, concurrency strategy, how admin bootstrap works, and any external services needed.

## Upload/HTTPS update (2026-10-25)
Django's default `DATA_UPLOAD_MAX_MEMORY_SIZE` (2.5 MiB) was smaller than the configured 10 MiB evidence cap. Because the raw evidence PUT view uses `request.body`, ordinary phone photos caused `RequestDataTooBig` and a 500 before the evidence service could validate them. `config/settings.py` now derives `DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_EVIDENCE_UPLOAD_BYTES + 1 MiB`; the service still enforces type, magic-byte, decode and max-size checks. An authenticated 7.0 MB JPEG upload through the HTTPS tunnel returned `204`; the temporary intent and stored object were deleted afterwards. A configuration test asserts the raw-body ceiling stays above the evidence cap.

## Final verification (2026-10-25)
66 pytest tests pass against real PostgreSQL; Ruff is clean; mypy reports no issues in 50 source files; `makemigrations --check --dry-run` reports no changes; `manage.py check` reports no issues. The endpoint list is reconciled with `apps/api/config/urls.py` in `docs/architecture/API_CONTRACT.md`.

## Campaign-scoped sites (2026-10-25)

Migration `corn.0003_campaign_sites_optional_location` was applied to the development database. It adds a nullable `DistributionSite.campaign` FK, makes site latitude/longitude nullable, and backfills existing sites from their earliest assignment campaign. Existing `GUDELE-02` and `MUNUKI-01` are attached to `Juba Central 2026`; no coordinates or historical records were changed.

Campaign creation accepts an optional `sites` name list and creates campaign + sites in one transaction. Site creation accepts a name alone, generates a unique `site_code`, allows an optional campaign, validates location pairs, and enforces case-insensitive duplicate names within a campaign. `PATCH /sites/{id}` can add, change, or clear both coordinates with an audit record. Assignment creation rejects a campaign-scoped site from another campaign and adopts legacy/global sites on first use. Analytics site rows are filtered by the selected campaign. The legacy map-sites view omits name-only sites; the SPA now uses the delivery-point map described below, so a name-only site does not suppress its delivery markers. Location is supporting metadata: distance is informational when both a fix and site reference exist, and location quality/geofence no longer emits warnings or gates approval.

**Verification (2026-10-25):** `make test-api` → **66 passed** (including 4 campaign-site tests and name-only geo/submission coverage); `make lint-api` → all checks passed; `make typecheck-api` → no issues in **50 source files**; `make migrate-check` → no changes; development migration applied successfully. `make test-e2e` → 8 passed.

**Unresolved issues:** Sites with no assignment campaign can remain global/nullable by design; the current UI always creates them inside a campaign. No map picker for site coordinates.


## Location policy and development cleanup (2026-10-25)

The confirmed product policy is **manual approval from any recorded place**. Backend changes:

- `corn.geo.evaluate_geo` no longer generates `GPS_MISSING`, `GPS_STALE`, `GPS_LOW_ACCURACY`, `OUTSIDE_GEOFENCE` or `EXIF_GPS_MISMATCH`. New records get `geo_status=PASS` when a fix exists and `UNAVAILABLE` when it does not. Distance is calculated only for context when both a fix and a site reference exist.
- `services/distribution.approve_delivery` no longer treats location as critical and no longer adds `LOCATION_EXCEPTION`. The only override-gated flags are `CAPTURE_TIME_MISMATCH`, `DUPLICATE_IMAGE_HASH` and `UNEXPECTED_FILE_TYPE`. A target overrun still requires an exception reason.
- `services/evidence` retains EXIF GPS/time and the EXIF-vs-reported distance as audit metadata but does not emit a location flag.
- Analytics/`views/sites` flag counts now use only non-location evidence-integrity flags.
- Tests were rewritten to prove far/stale/inaccurate/missing fixes produce no warnings yet still approve, while non-location evidence integrity coverage remains.

**Development data cleanup:** after a database dump and private-storage tar backup under `/tmp/opencode/corn-backups/` (`corn_tracker_dev_20261025T172013Z.dump`, `storage-data_20261025T172013Z.tar.gz` plus SHA-256 sums), the development database was reduced to:

- campaign `2f75b3b0-fb12-48e4-bbc5-1b5842162b10` (Kolhapur), site `28bc1000-6fde-4aee-b278-518ed30f93a9` (KOLHAPUR, name-only), assignment `c909b2a3-8f7a-4cc4-aa90-43394939a679` (Amina);
- approved record `2437b6a2-9b68-48fb-8bc7-3d66554a435d` (1 kg) and evidence `b8d95736-b72f-41a5-8840-c15daa4f30d1`;
- the minimum funding chain: opening receipt 50,000 kg to central, 20,000 kg allocation to Amina and the 1 kg delivery to the Kolhapur site;
- three user logins (admin, Amina, inactive John), one settings row set to `Asia/Kolkata`, and the retained audit events.

Deleted: 7 records, 7 evidence rows/files, 3 movements, 2 assignments, 2 Juba sites, 1 Juba campaign, 3 non-retained accounts, 16 upload intents, 2 invitations and 62 dummy audit rows. The append-only triggers were temporarily disabled for that transactional cleanup and confirmed `O` (enabled) afterward. The retained balances were not rewritten; the 50,000/20,000 funding chain is deliberately kept because it is the ledger backing for the approved record.

**Verification (2026-10-25):** `make test-api` → 66 passed; `make lint-api` → clean; `make typecheck-api` → 50 source files clean; `make migrate-check` → no changes. Database verification after cleanup: users 3, campaigns 1, sites 1, assignments 1, records 1, evidence 1, accounts 3, movements 3, upload intents 0, invitations 0, storage files 1.

## Delivery-only admin map (2026-10-25)

Added admin-only `GET /api/v1/analytics/map-deliveries` (`bbox`, `campaign_id`, `distributor_user_id`). The service returns one point per delivery record that has a captured latitude/longitude and status `SUBMITTED` or `APPROVED`; rejected/cancelled claims are excluded. It returns site and distributor display fields, quantity, status, submitted time and location metadata, but no evidence URLs. Site reference coordinates and sites without deliveries are not involved, so the retained approved 1 kg Kolhapur record is visible even though its site is name-only. The older `/analytics/map-sites` endpoint remains for API compatibility but is no longer used by the SPA. Authorization remains `IsAdminRole`, and invalid bbox input returns the existing `422`.

**Verification:** `make test-api` → 67 passed (including delivery-map status/bbox/scope coverage and rejected-claim exclusion); `make lint-api` → clean; `make typecheck-api` → no issues in 50 source files; `make migrate-check` → no changes. No schema change.

## Post-remediation verification (2026-10-26)

The 2026-10 audit W0/W1 backend findings are remediated and regression-covered: scoped/payload-bound idempotency with fail-closed legacy keys, compensating reversals with reservation/overdraw guards, assignment-locked target approval, raced first-site account creation, distributor campaign/site-stock scope, hidden internal notes, direct-S3 completion with size/SHA/bounded-read/tamper checks, trusted-proxy XFF handling, storage-aware readiness and a bounded process-local limiter.

Current verification: `make test-api` → **98 passed**; Ruff and mypy clean in **51 source files**; migration `0004` applies and `makemigrations --check` reports no drift; Playwright E2E **9 passed**. External probes: **12 remediation probes + 1 simulated-S3 probe passed**. Real provider S3/CORS/KMS, production restore/load and the multi-worker shared limiter remain external.

## Railway/Vercel deployment preparation (2026-10-28)

Added Railway host auto-allowlisting, managed Bucket variable fallbacks,
virtual-host S3 addressing (required by Railway Buckets), a single
`FRONTEND_ORIGIN` for CORS/CSRF, and the Railway/Docker deployment scripts.
Current verification: `make test-api` → **98 passed**; Ruff/mypy clean in 51
source files; migration drift clean. Real provider deployment remains external.
