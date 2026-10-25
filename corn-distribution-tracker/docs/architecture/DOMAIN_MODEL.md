# Domain Model and State Machines

## Canonical data rules
- `quantity_kg`: positive `NUMERIC/DECIMAL` for movement/record quantities; no floating point. Currency-like decimal arithmetic patterns apply even though corn is not money.
- Latitude range [-90, 90], longitude range [-180, 180]. Use WGS84 / SRID 4326 for stored locations.
- Store timestamps in UTC (`timestamptz`); render in the campaign/organization timezone setting (default from explicit config; do not infer from the viewer when comparing dates).
- IDs are opaque UUIDs. Use `created_at`, `updated_at` where mutable; append-only ledger/audit/evidence lifecycle records retain historic fields.

## Core tables
### users
`id`, `email_normalized` (unique), `display_name`, `password_hash` or external auth reference, `role` (`ADMIN|DISTRIBUTOR`), `is_active`, `must_reset_password`, `last_login_at`, `created_at`, `updated_at`. Store no plain-text passwords or reusable invite tokens.

### auth_sessions
Django's database-backed sessions store a random session key and serialized auth state in `django_session`; the browser holds only an HttpOnly `sessionid` cookie. CSRF uses a separate double-submit cookie and `X-CSRFToken` header. Do not store raw reusable session or invitation/reset tokens in application tables.

### campaigns
`id`, `name`, `reference_code` (unique), `starts_at`, `ends_at`, `status` (`DRAFT|ACTIVE|PAUSED|CLOSED`), `timezone`, notes, creator, timestamps. Display-unit and bag conversion settings live in `organization_settings`, not on each campaign.

### distribution_sites
`id`, `name`, `site_code` (unique), `campaign_id` (FK, nullable only for legacy/global records), `address_text`, optional region, `latitude` nullable, `longitude` nullable, `geofence_radius_m`, `max_acceptable_accuracy_m`, `is_active`, notes, creator, timestamps. Sites are configured inside one campaign; the current UI creates them during campaign setup or from the selected campaign panel. A site can belong to at most one campaign. Names are unique per campaign case-insensitively at the service boundary; a database-wide unique `site_code` is generated from the name when one is not supplied. Latitude/longitude must be supplied together and validated when present. Location edits are audit logged. `geofence_radius_m` and `max_acceptable_accuracy_m` are retained as legacy schema fields; they are not used for approval. A name-only site has no reference coordinates; distance is null and no location warning is produced. Historical records are not recalculated when a location is added.

### distributor_assignments
`id`, `campaign_id`, `site_id`, `distributor_user_id`, `target_quantity_kg`, `due_at` nullable, `status` (`ACTIVE|PAUSED|COMPLETE`), notes, created_by, timestamps. Unique assignment policy must be explicit (e.g., one active assignment per campaign + site + distributor); if multiple distributors can serve one site, analytics must aggregate correctly and identify each assignment.

### inventory_accounts
`id`, `account_type` (`CENTRAL|DISTRIBUTOR|SITE`), optional `owner_user_id` and/or `site_id`, `name`, `is_active`, timestamps. Exactly one central account for the initial organization; unique account per distributor and site.

### stock_movements
Append-only ledger: `id`, `movement_type` (`RECEIPT|TRANSFER|DELIVERY|RETURN|LOSS|ADJUSTMENT|REVERSAL`), `source_account_id` nullable for receipt, `destination_account_id` nullable for loss, `quantity_kg NUMERIC`, `reference_type`, `reference_id`, `idempotency_key`, `occurred_at`, `posted_at`, `created_by`, `reason`, `reversal_of_id` nullable, metadata, created_at. Use check constraints to enforce valid account/quantity semantics and uniqueness of idempotency keys where applicable. Posted movements are immutable.

### distribution_records
`id`, `campaign_id`, `assignment_id`, `site_id`, `distributor_user_id`, `quantity_kg NUMERIC`, `status` (`DRAFT|SUBMITTED|APPROVED|REJECTED|CANCELLED`), `idempotency_key` unique per submitting user or scope, `client_created_at`, `submitted_at`, `reviewed_at`, `reviewed_by`, `review_reason`, `review_exception_reason`, `stock_movement_id` unique nullable, `notes`, `location_latitude`, `location_longitude`, `location_accuracy_m`, `location_timestamp`, `device_reported_location_time`, `distance_to_site_m` nullable (informational; null when the site has no reference coordinates or no GPS fix), `geo_status` (new records: `PASS` when a fix exists, `UNAVAILABLE` when not; `WARNING|EXCEPTION` are legacy), `geo_flags` JSON (new records contain only non-location evidence-integrity flags; legacy location flags may remain), created_at and updated_at. Only SUBMITTED can transition to APPROVED/REJECTED. Location never blocks approval; an exception reason is required only for non-location evidence integrity or an exceeded target. Approved records are immutable for quantity/site/distributor; corrections create a new record plus compensating movement as needed.

### photo_evidence
`id`, `distribution_record_id`, `storage_key`, `thumbnail_key` nullable, `content_type`, `size_bytes`, `sha256_hex`, capture source (`CAMERA|FILE_PICKER|OFFLINE_CAMERA`), `client_captured_at`, `server_received_at`, EXIF GPS/time values if extracted (context only), metadata check result, duplicate-of pointer or flag, non-location evidence-integrity validation flags JSON, uploader_user_id, lifecycle status, created_at. The current build stores `thumbnail_key` as a nullable field but does not generate thumbnail derivatives; authorized views load the private original. Keep bucket/object ACL private.

### audit_events
`id`, `actor_user_id` nullable for system, `action`, `target_type`, `target_id`, `occurred_at`, request_id/correlation_id, reason, safe before/after summary JSON, source/IP/device details where appropriate and lawful. Never store passwords, session cookies, CSRF secrets, signed URLs, image bytes or unnecessary sensitive data.

### organization_settings
Single-row settings for the initial single-organization release: `id`, `timezone`, `default_display_unit`, `kg_per_bag` nullable, `max_capture_time_drift_seconds`, updated_by and updated_at. `default_geofence_radius_m`, `max_acceptable_gps_accuracy_m` and `max_location_age_seconds` remain as legacy columns for compatibility but are not used for review and are not editable in the current UI. Strictly allowlist fields; do not store arbitrary infrastructure secrets or pretend environment-only settings are UI-editable.

### notifications (optional but recommended; not implemented)
In-app event for assignment/review status changes: user, type, target reference, message-safe payload, read_at, created_at. The current build has no notifications table or feed; review feedback is visible in the relevant submission screens. Email/SMS notifications are not a first-release dependency.

## State machine
- Submission: `DRAFT -> SUBMITTED -> APPROVED | REJECTED`; `DRAFT -> CANCELLED` and `SUBMITTED -> CANCELLED` only under documented policy. No `REJECTED -> APPROVED` shortcut: submit a corrected new record or create an audited admin resolution flow.
- Evidence is uploaded first to a pending/private storage state, validated, then associated with the distribution record. Orphan upload cleanup is scheduled/operationally documented.
- Approval is an atomic service operation. Lock submission + affected stock accounts, ensure pending state and stock reservation, write movement once, attach movement ID, transition to approved, append audit event. If any step fails, all DB changes roll back.
- Rejection writes review reason/status/audit event but no stock movement.

## Derived quantities
Do not store derived balances as independently editable source-of-truth fields. Derive ledger balances from posted movements or use a transactionally maintained projection that can be rebuilt and reconciled. Pending submissions are reservations, not posted stock movements.
