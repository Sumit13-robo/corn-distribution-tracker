# API Contract (v1)

Base path: `/api/v1`. Use JSON for normal request/response bodies. Return a consistent error shape: `{"error":{"code":"VALIDATION_ERROR","message":"Human-safe summary","request_id":"...","details":[]}}`. Never return stack traces, SQL, tokens, storage credentials, or private file keys. Standard pagination: `limit` (default 25, capped e.g. 100), `cursor` or stable `page/offset` where justified, plus `next_cursor`/total only when appropriate. All list filters run server-side and honor authorization scope.

## Authentication (Django session cookies)
- `GET /auth/csrf` — issues the CSRF cookie and returns `{"csrf_token":"..."}` for browser bootstrap. Login, `GET /auth/me` and this endpoint also ensure the cookie is present.
- `POST /auth/login` — email/password; rate limited; creates a database-backed server session and sets the HttpOnly `sessionid` cookie. Returns `{"user":{...}}`; no bearer access token or refresh token is issued.
- `GET /auth/me` — current sanitized session user; a bare user object. A missing/expired session returns `401`.
- `POST /auth/logout` — requires the session plus `X-CSRFToken`; deletes the server session and clears the cookie.
- `POST /auth/change-password` — current password + new password; rotates the session credential.
- `POST /auth/forgot-password`, `POST /auth/reset-password` — generic response that does not reveal account existence. No mail transport ships; an operator issues a one-time reset token with `manage.py issue_password_reset` and delivers it through a secure channel.
- `POST /auth/accept-invitation` — consumes a one-time invitation token and sets the new account password.
- `POST /admin/users/invitations` — admin-only provisioning. The raw invitation token is returned once to the creating admin for secure delivery; it is never logged or returned by list endpoints. A one-time CLI (`manage.py create_admin`) creates the first admin.
- Browser mutations require a first-party cookie and Django's double-submit CSRF check: send the `csrftoken` cookie value in `X-CSRFToken`. Unsafe requests also validate `Origin` when supplied.

## Campaigns and users
- `GET/POST /campaigns`, `GET/PATCH /campaigns/{id}` — admin writes; role-scoped reads.
- `GET/POST /admin/distributors`, `GET/PATCH /admin/distributors/{id}`, `POST /admin/distributors/{id}/deactivate` — admin-only.
- `GET /distributors/me/assignments` — distributor sees own assignments only.

## Sites and assignments
- `GET /sites` — admin sees all; distributor sees only sites associated with active assignments. Support bounds/bbox or campaign/status filters for map.
- `POST /sites`, `GET /sites/{id}`, `PATCH /sites/{id}`, `POST /sites/{id}/deactivate` — writes admin-only; all coordinate edits audit logged.
- `POST /assignments`, `GET /assignments`, `GET/PATCH /assignments/{id}` — admin manages assignments; distributor only reads own assignment detail. Assignment overage policy is explicit.

## Inventory
- `GET /inventory/summary` — account-scoped summary; admin org-wide, distributor own stock only.
- `GET /inventory/accounts/{id}/ledger` — admin or owner; paginated immutable movement history.
- `POST /inventory/receipts` — admin-only receipt to central stock.
- `POST /inventory/allocations` — admin-only central → distributor transfer and any assignment target changes.
- `POST /inventory/adjustments` — admin-only, reason mandatory, validated type, no silent negative balance.
- All mutation requests accept `Idempotency-Key` header or explicit idempotency key. Return canonical quantity/kg and display metadata as appropriate.

## Delivery and evidence
- `POST /evidence/upload-intents` — authenticated, scoped request returns short-lived upload instructions for a private object key; enforce size/content-type constraints and bind intent to user/record context.
- `POST /deliveries` — distributor submits quantity, assignment/site, capture/location metadata, evidence upload references and idempotency key. Must verify assignment ownership and evidence ownership/state.
- `GET /deliveries`, `GET /deliveries/{id}` — role-scoped list/detail.
- `POST /deliveries/{id}/approve` — admin only; optional exception override + reason. Transactional, idempotent ledger posting.
- `POST /deliveries/{id}/reject` — admin only; rejection reason required.
- `POST /deliveries/{id}/cancel` — only allowed in states/policy; never erase posted movements.
- `GET /evidence/{id}/view-url` — authorized short-lived signed URL, with private metadata permitted to current user/admin.

## Analytics and exports
- `GET /analytics/overview?campaign_id=&from=&to=` — role-scoped KPI metrics with metric names and units.
- `GET /analytics/distributors` — admin only; scoped filters and clear denominators.
- `GET /analytics/sites` — admin only.
- `GET /analytics/map-sites?bbox=&campaign_id=&status=` — scoped map features; return coordinates + site summary but not raw private evidence URLs.
- `GET /exports/distributions.csv?...` — authorized server-side filtered CSV; safe CSV escaping to prevent formula injection; set download headers and audit export action.

## Settings and audit
- `GET /settings` — return the allowlisted organization settings visible to the current user.
- `PATCH /settings` — admin only; allowlist timezone, display unit, explicit kg-per-bag, geofence radius and GPS accuracy thresholds. Audit every change; never expose or mutate infrastructure secrets here.
- `GET /audit/events` — admin-only paginated audit history with server-side date/actor/action/target filters and sanitized payloads; there is no general edit/delete endpoint.
- `POST /admin/bootstrap` is deliberately not part of the API. Create the first administrator through the one-time CLI.

## Response requirements
- Every relevant record includes `id`, status, and UTC ISO-8601 timestamps.
- Distribution records include `site_id`, `site_code`, `site_name`, `distributor_user_id` and `distributor_name` so review screens do not show opaque UUIDs.
- Quantity responses return `quantity_kg` plus optional display conversion object with unit and configured factor.
- Pagination and filters apply server-side.
- Validation errors use field paths; conflicts such as insufficient stock or illegal state transitions return `409` with stable machine code. Invalid query strings return `422`.
- `401` means missing/expired auth; `403` means authenticated but not allowed; `404` may be used for inaccessible resource IDs to avoid enumeration.
- Add `request_id` to responses/logs. Use ETags or updated-at checks for mutable admin forms if needed to prevent lost updates.
