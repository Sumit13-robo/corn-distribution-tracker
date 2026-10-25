# API Contract (v1)

Base path: `/api/v1` unless noted. JSON is used for normal request/response bodies; the CSV export is the exception.

## Session and CSRF

- Authentication is a database-backed Django session. `POST /auth/login` sets the HttpOnly `sessionid` cookie and returns `{"user": {...}}`. No bearer access token or refresh token is issued.
- Authenticated unsafe requests (`POST`, `PUT`, `PATCH`, `DELETE`) are protected by DRF's `SessionAuthentication`, which enforces the `csrftoken` cookie plus the matching `X-CSRFToken` header. `GET /auth/csrf` issues the cookie and returns `{"csrf_token":"..."}`; `GET /auth/me` also refreshes it. Unauthenticated login/recovery endpoints are not session-authenticated, but all unsafe requests with an `Origin` header are checked against `CORS_ALLOWED_ORIGINS` and the request origin.
- Login is rate limited by client IP. The limiter counts **failed** attempts only (10 failures per 5 minutes); successful sign-ins do not consume the budget. A `429` includes `Retry-After` and `details:[{"retry_after":seconds}]`. Credential failures stay a generic `401` to avoid account enumeration.
- Logout deletes the server session. Deactivation and password reset revoke existing sessions. Password change rotates the current session key; other active sessions are not explicitly revoked by this build.
- Evidence blob URLs are the only public resource URLs; they are short-lived signed URLs generated after authorization.

## Errors

All errors use:

```json
{"error":{"code":"VALIDATION_ERROR","message":"Human-safe summary","request_id":"...","details":[]}}
```

Stable codes include `VALIDATION_ERROR`, `UNAUTHENTICATED`, `FORBIDDEN`, `NOT_FOUND`, `CONFLICT`, `INSUFFICIENT_STOCK`, `ILLEGAL_STATE`, `DUPLICATE`, `RATE_LIMITED`, `REASON_REQUIRED` and `INTERNAL_ERROR`.

Status conventions:
- `400` — domain/application error with a specific code.
- `401` — no or expired session.
- `403` — authenticated but role/ownership denied.
- `404` — missing resource, or a resource outside the caller's scope (deliberately indistinguishable from missing).
- `409` — state conflict such as duplicate approval or inactive assignment.
- `422` — request/query validation failure.
- `429` — rate limited; includes `Retry-After` when known.
- `500` — unexpected error with a request id; no stack traces or internal details.

## Pagination

Paginated list endpoints (`/campaigns`, `/sites`, `/assignments`, `/deliveries`, `/inventory/.../ledger`, `/admin/distributors`, `/audit/events`) return:

```json
{"items":[],"total":0,"limit":25,"offset":0}
```

`limit` defaults to 25 and must be 1–100; `offset` must be non-negative. Invalid pagination returns `422`. There is no cursor pagination.

## Endpoints

### Health

| Method | Path | Access | Notes |
|---|---|---|---|
| GET | `/health/live` or `/api/v1/health/live` | Public | Process liveness. |
| GET | `/health/ready` or `/api/v1/health/ready` | Public | Readiness, including database and evidence-storage checks. |

### Authentication and account lifecycle

| Method | Path | Access | Notes |
|---|---|---|---|
| POST | `/auth/login` | Public | Email/password; sets session and CSRF cookies; rate limited. |
| GET | `/auth/me` | Session | Current user; also sets the CSRF cookie. |
| GET | `/auth/csrf` | Public | Issues CSRF cookie and returns the token. |
| POST | `/auth/logout` | Session | Deletes the session. |
| POST | `/auth/change-password` | Session | Requires `current_password`, `new_password`; rotates the current session key. |
| POST | `/auth/forgot-password` | Public | Records a request; always generic. No mail is sent. |
| POST | `/auth/reset-password` | Public | One-time token + new password; revokes sessions. |
| POST | `/auth/accept-invitation` | Public | One-time invitation token + password; activates the account. |
| GET | `/admin/users/invitations` | Admin | Latest 100 invitations; raw tokens are never returned. |
| POST | `/admin/users/invitations` | Admin | Creates an invitation; returns `invite_token` **once**. |

### Distributors

| Method | Path | Access | Notes |
|---|---|---|---|
| GET | `/admin/distributors` | Admin | Filters: `search` (name/email), `limit`, `offset`. |
| GET | `/admin/distributors/{id}` | Admin | Detail with stock, reserved/available, assignment counts and invite state. |
| PATCH | `/admin/distributors/{id}` | Admin | Allowlisted fields: `display_name`. |
| POST | `/admin/distributors/{id}/deactivate` | Admin | Deactivates the account and revokes sessions. |
| GET | `/distributors/me/assignments` | Session (distributor self-service) | The signed-in distributor's assignments. |

There is no `POST /admin/distributors`; new distributors are created through an invitation accepted by the recipient.

### Campaigns, sites and assignments

| Method | Path | Access | Notes |
|---|---|---|---|
| GET | `/campaigns` | Session | Filters: `status`, `limit`, `offset`. |
| POST | `/campaigns` | Admin | `name`, `reference_code`, optional dates/timezone/notes/status, and optional `sites` (list of place names). Campaign + sites are created in one transaction; duplicate names within the request are ignored case-insensitively. |
| GET | `/campaigns/{id}` | Session | Campaign detail. |
| PATCH | `/campaigns/{id}` | Admin | Allowlisted fields; closed campaigns cannot be reopened. Sites are not edited through this route. |
| GET | `/sites` | Session | Admin: all sites; distributor: assigned sites only. `search`, `limit`, `offset` apply to both; `active_only` and `campaign_id` are admin-only. Coordinates may be `null`. |
| POST | `/sites` | Admin | `name` required; optional `campaign_id`, `site_code`, coordinates, address/region, and legacy geofence/accuracy fields. A missing `site_code` is generated from the name. Name-only sites omit both coordinates. |
| GET | `/sites/{id}` | Session | Distributors receive `404` for unassigned sites. Coordinates may be `null`. |
| PATCH | `/sites/{id}` | Admin | Allowlisted fields including optional location. Latitude/longitude must be supplied together or both set to `null`; location changes are audited. Legacy geofence/accuracy fields are accepted for schema compatibility but no longer gate review. |
| GET | `/sites/{id}/progress` | Session | Optional `campaign_id`; scoped to the distributor's own records. |
| POST | `/sites/{id}/deactivate` | Admin | Deactivates a site. |
| GET | `/assignments` | Session | Optional `campaign_id`; distributors see their own assignments. |
| POST | `/assignments` | Admin | Links a site, distributor and optional campaign with a target in kg. A campaign-scoped site cannot be assigned to a different campaign. |
| GET | `/assignments/{id}` | Session | Scoped detail. |
| PATCH | `/assignments/{id}` | Admin | Allowlisted assignment fields. |

Sites are configured inside a campaign in the current UI (`/campaigns`); `/sites` remains the API resource and `/sites` in the SPA redirects to `/campaigns`. A site has at most one campaign (`campaign_id`, nullable only for legacy/global records). New sites should be created with `campaign_id`. A name alone is enough: coordinates may be added later through `PATCH /sites/{id}`.

A site location is optional context. When a site has no latitude/longitude, submissions that use it still capture device GPS when available and `distance_to_site_m` is `null`. The admin delivery map plots only delivery-record locations, so a name-only site does not suppress a delivery marker; evidence review simply omits the site reference marker. Whenever a fix is recorded, a delivery is approvable from that place: new records use `geo_status` `PASS` (fix captured) or `UNAVAILABLE` (no fix), and no `OUTSIDE_GEOFENCE`/GPS-quality flag is generated. When both a fix and a site reference exist, distance is stored for context only; it never blocks approval or requires an exception. Historical location flags remain readable but are not generated or shown as warnings. Existing records are not recalculated when a site location is added later.

### Inventory ledger

| Method | Path | Access | Notes |
|---|---|---|---|
| GET | `/inventory/summary` | Session | Central/distributor/site balances; distributors see their own holdings. |
| GET | `/inventory/accounts/{id}/ledger` | Session | Scoped movement history; admin or account owner. |
| POST | `/inventory/receipts` | Admin | Receives stock into an account. Supports `Idempotency-Key`. |
| POST | `/inventory/allocations` | Admin | Allocates central stock to a distributor. Supports `Idempotency-Key`. |
| POST | `/inventory/adjustments` | Admin | Loss/return/correction with required reason. Supports `Idempotency-Key`. |
| POST | `/inventory/movements/{id}/reversal` | Admin | Compensating reversal with required reason. |
| GET | `/inventory/display-unit` | Session | Requires `quantity_kg`; optional `unit` overrides the configured display unit. Returns the converted display value and factor label. |

Quantities are decimal strings in kg in responses. Write endpoints accept a `unit` of `KG`, `QUINTAL`, `TONNE` or `BAG`; `BAG` requires an organization `kg_per_bag` factor. Ledger and audit rows are append-only at the database level.

### Deliveries and evidence

| Method | Path | Access | Notes |
|---|---|---|---|
| GET | `/deliveries` | Session | Filters: `status`, `campaign_id`, `site_id`, `distributor_user_id`, `from`, `to`, `limit`, `offset`. Distributors are scoped to their own records. |
| POST | `/deliveries` | Session (distributor flow) | Creates a submitted record for the caller's assignment; supports `Idempotency-Key`; rate limited per user. Requires an assignment, quantity/unit, evidence specs and optional location/notes. |
| GET | `/deliveries/{id}` | Session | Scoped detail. |
| POST | `/deliveries/{id}/approve` | Admin | Optional `review_note`; `exception_reason` is required only for non-location evidence-integrity flags or an exceeded assignment target. Posts exactly one stock movement. Supports `Idempotency-Key`. |
| POST | `/deliveries/{id}/reject` | Admin | Required `reason`; releases the reservation. |
| POST | `/deliveries/{id}/cancel` | Owner or admin | Only `DRAFT`/`SUBMITTED`; posted corrections use a reversal. |
| POST | `/evidence/upload-intents` | Session | Creates a private upload intent; rate limited per user. Used by the distributor flow. |
| PUT | `/evidence/objects/{intent_id}` | Session (owner) | Raw image body with intent headers; JPEG/PNG/WebP, size cap. |
| GET | `/evidence/{id}/view-url` | Session | Authorized short-lived view URL; admin or the uploader. |
| GET | `/evidence/blob/{id}` | Signed URL | Serves the private object only with a valid signature/expiry. |

Evidence uploads are decoded, content-sniffed, SHA-256 hashed and stored privately. The API records EXIF/GPS and non-location evidence-integrity flags as advisory indicators; location is supporting metadata and never a review gate. It does not claim spoofing-proof capture.

### Analytics, export, settings and audit

| Method | Path | Access | Notes |
|---|---|---|---|
| GET | `/analytics/overview` | Session | Optional `campaign_id`, `from`, `to`; scoped for distributors. |
| GET | `/analytics/distributors` | Admin | Optional `campaign_id`, `from`, `to`. |
| GET | `/analytics/sites` | Admin | Optional `campaign_id`, `from`, `to`. With `campaign_id`, only sites belonging to that campaign are returned; name-only sites are included. |
| GET | `/analytics/map-deliveries` | Admin | Optional `bbox=min_lng,min_lat,max_lng,max_lat`, `campaign_id`, `distributor_user_id`. Returns one point per delivery record with a captured location and status `SUBMITTED` or `APPROVED`. Rejected/cancelled claims are excluded. Site reference coordinates and sites without deliveries are never returned. |
| GET | `/analytics/map-sites` | Admin | Legacy site-status view retained for API compatibility; the SPA delivery map does not use it. Optional `bbox`, `campaign_id`, `distributor_user_id`. Returns `COMPLETE`, `PENDING`, `IN_PROGRESS` or `NO_ACTIVITY` per site with reference coordinates. |
| GET | `/exports/distributions.csv` | Admin | Filters: `status`, `campaign_id`, `distributor_user_id`, `from`, `to`; capped at 10,000 rows; the export is audited. |
| GET | `/settings` | Session | Organization settings. |
| PATCH | `/settings` | Admin | Allowlisted: `timezone`, `default_display_unit`, `kg_per_bag`, `max_capture_time_drift_seconds`. `default_geofence_radius_m`, `max_acceptable_gps_accuracy_m` and `max_location_age_seconds` remain accepted for schema compatibility but are legacy and no longer affect review; the UI does not edit them. |
| GET | `/audit/events` | Admin | Filters: `action`, `actor_user_id`, `target_type`, `target_id`, `from`, `to`, `limit`, `offset`. |

## Response shapes (selected)

- `user`: `id`, `email`, `display_name`, `role`, `is_active`, `must_reset_password`, `last_login_at`.
- `campaign`: `id`, `name`, `reference_code`, `starts_at`, `ends_at`, `status`, `timezone`, `notes`, timestamps.
- `site`: `id`, `site_code`, `name`, `campaign_id`, `address_text`, `region`, nullable `latitude`/`longitude`, legacy `geofence_radius_m`/`max_acceptable_accuracy_m` (not used for review), `is_active`, notes for admins.
- `assignment`: `id`, `site_id`, `distributor_user_id`, `campaign_id`, `target_quantity_kg`, `status`, timestamps.
- `delivery`: record id, assignment/site/campaign/distributor references, `quantity_kg`, `status`, `geo_status` (`PASS`/`UNAVAILABLE` for new records), non-location evidence `geo_flags`, informational distance/accuracy/time metadata, evidence list, review fields, stock movement id when approved. Legacy location flags may remain on historical rows but are not displayed as warnings.
- `movement`: id, account, movement type, signed/quantity fields, reference, actor, reversal link, timestamps.
- `overview`: stock balances, submitted/approved/rejected kg, open review count, target/remaining/over-target kg, evidence completeness and non-location evidence-integrity flagged count.
- `map delivery`: delivery record id, site id/code/name, campaign id, distributor id/name, quantity kg, status (`SUBMITTED`/`APPROVED`), submitted timestamp and captured `location_latitude`/`location_longitude`/accuracy/time. No evidence URLs.
- `map site` (legacy): id, site code/name, coordinates, target/approved/pending/remaining kg, submission count, status, last visit, flag indicator.

## Idempotency and concurrency

- `POST /deliveries`, inventory postings and delivery approval honor an `Idempotency-Key` header. Reusing a key returns the existing result instead of creating a second record or movement.
- Ledger transitions use row locks and unique idempotency scopes; approval posts at most one stock movement.
- Stock movements and audit events are append-only. Corrections use compensating movements/reversals; approved records are not destructively edited.

## Out of scope for this build

The API does not expose notifications, re-invite/reset-from-list, image thumbnails, a full audit diff viewer, or OpenAPI docs. The SPA delivery map calls `/analytics/map-deliveries` and sends only the campaign filter; `bbox` and `distributor_user_id` remain available to API clients.
