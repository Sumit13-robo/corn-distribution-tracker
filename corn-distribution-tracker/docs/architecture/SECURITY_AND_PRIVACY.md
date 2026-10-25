# Security, Privacy, and Threat Model

## Assets to protect
User credentials and sessions; site and distributor records; geotagged photos and image metadata; inventory history; location coordinates; invitation/reset tokens; signed storage URLs; audit trail; database and storage credentials.

## Authentication/session
- Hash passwords using Argon2id or another currently recommended password hash with reviewed parameters; never encrypt for reversibility or log passwords.
- Enforce reasonable password policy and breached-password checks if a suitable provider exists; rate-limit login/reset/invitation endpoints and use generic messages for account recovery.
- Use Django's database-backed server sessions with an HttpOnly, Secure, SameSite cookie in production. Protect authenticated cookie-driven mutations with Django's CSRF check (`csrftoken` cookie + `X-CSRFToken`) and validate `Origin` when present. Keep session cookies and credentials out of localStorage and browser-readable response bodies. The CSRF token is intentionally readable by the SPA, but it is useless without the session cookie.
- Configure HTTPS at the edge; set Secure cookies in production; set trusted proxy headers correctly; disable permissive wildcard CORS in production.
- Admin accounts should support/require MFA where feasible before broad production rollout. If MFA is not implemented in the first build, explicitly list it as a launch risk rather than pretending it exists.
- Create first admin through a controlled CLI/bootstrap process; prevent public role elevation.

## Authorization
- Enforce role, ownership and assignment scope in API dependencies/services and test it with adversarial IDs. Use deny-by-default.
- Do not trust role/owner IDs supplied by the client. Derive identity from the authenticated session.
- Evidence view URLs are signed only after rechecking user access; expire quickly; do not persist signed URLs in the database or logs.

## API/app security
- Validate request schemas, content types, payload sizes, dates, coordinates, units, quantities and enum states.
- Use ORM parameterization; avoid SQL string interpolation for query parameters.
- Apply upload MIME sniffing, extension allowlist, max byte limits, image decoding/re-encoding where appropriate, malware-scanning hooks if available, and reject unexpected file types. Content-Type from browser alone is not trusted.
- Apply secure headers, CSP compatible with the app/map provider, request size limits, CSRF/Origin controls where relevant, dependency scanning and lockfile updates.
- Redact passwords, auth headers, tokens, invite/reset values, signed URLs, raw image bytes, and unnecessary exact coordinates from routine logs.
- CSV exports escape cells beginning with `=`, `+`, `-`, or `@` and respect access scope.

## Photo and location privacy
- Explain that site photos and location are collected for delivery verification/accountability; request permission only in the delivery workflow.
- Capture/store only what is needed. Do not run background location tracking, location collection outside an active report, face recognition, or covert monitoring.
- Keep originals private and access-controlled. If transformations are performed, keep original evidence immutable under the retention policy and label the transformed preview as derivative.
- Define configurable retention and deletion/legal-hold policies. Audit access to evidence if required by the operator's policy. Avoid retaining offline image copies longer than necessary.
- Geolocation values may be inaccurate or spoofed. Store accuracy and validation context; never represent as absolute proof.
- Browser geolocation requires a secure context. Serve the SPA over HTTPS for real device capture; an HTTP LAN development URL only supports UI testing. When `window.isSecureContext === false`, show explicit HTTPS guidance rather than implying the site permission is wrong.
- Development HTTPS tunnels are public and temporary. Use synthetic data, keep authentication enabled, add only the exact tunnel origin to `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`, and stop the tunnel when the demo ends. Use a trusted HTTPS reverse proxy for real data.

## Data integrity and audit
- Stock movements and audit events are append-only; PostgreSQL triggers reject updates/deletes, and DB roles should still be restricted from unnecessary destructive privileges.
- Use transactions, row locks/concurrency control, foreign keys, unique constraints, check constraints and idempotency keys.
- Admin adjustments and evidence exceptions require a reason. Sensitive access and state changes create audit events.
- Backups must be encrypted, access restricted and restore-tested. Keep application, database and object-store credentials separate and rotate them.

## Minimum launch review
Threat-model account takeover, IDOR/BOLA, overposting, double-spend/race conditions, signed-URL leakage, public object ACLs, replayed/duplicate submissions, GPS/EXIF metadata mismatch (recorded for context, never a location gate), upload malware, XSS/CSRF, CSV injection, leaked environment secrets, excessive log retention, and untested restore. Document unresolved issues before go-live.
