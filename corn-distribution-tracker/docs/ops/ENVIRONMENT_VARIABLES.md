# Environment Variables

Use `.env.example` with safe placeholders only. Django loads the repository-level `.env` first, then `apps/api/.env`; real environment variables win. Django validates configuration at startup and fails fast on insecure production settings. Keep `.env` out of source control.

## API (Django)
- `APP_ENV` — `development|test|staging|production`. `production` enables the fail-fast policy.
- `APP_NAME` — service/display name.
- `API_V1_PREFIX` — normally `/api/v1`.
- `DATABASE_URL` — PostgreSQL URL (`postgresql+psycopg://user:pass@host:port/db`); credentials come from a secret manager in production. PostGIS is not required.
- `DB_CONN_MAX_AGE` — Django database connection lifetime in seconds. The code default is `60`; the template uses `0` for the threaded development server, which avoids accumulating idle connections. Gunicorn deployments may use `30`-`60` within the database connection budget.
- `SECRET_KEY` — high-entropy Django secret (for example `openssl rand -hex 48`). The development sample is rejected in production.
- `SESSION_TTL_DAYS` — database-backed session/cookie lifetime in days (default 14).
- `SESSION_COOKIE_NAME` — default `sessionid`; HttpOnly is always enabled.
- `ALLOWED_HOSTS` — comma-separated hostnames; `*` is rejected in production.
- `CORS_ALLOWED_ORIGINS` — exact SPA origins, comma separated. Never a wildcard when credentials are enabled.
- `CSRF_TRUSTED_ORIGINS` — exact origins that may send unsafe requests through a proxy. Add the public SPA origin when a reverse proxy terminates TLS or strips a port.
- `CORS_ALLOW_CREDENTIALS` — must remain `true` for cookie sessions (default).
- `COOKIE_SECURE` — `true` in production. Controls both session and CSRF cookies.
- `COOKIE_SAMESITE` — `Lax` (default) or `Strict`; `None` requires `COOKIE_SECURE=true`.
- `COOKIE_DOMAIN` — optional cookie domain; empty means host-only (recommended).
- `TRUST_X_FORWARDED_PROTO` — enable only behind a trusted proxy that overwrites the header.
- `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD` — TLS/HSTS behavior behind the ingress.
- `STORAGE_MODE` — `local` for development/tests or `s3` for production private object storage.
- `STORAGE_ENDPOINT_URL`, `STORAGE_REGION`, `STORAGE_BUCKET`, `STORAGE_ACCESS_KEY_ID`, `STORAGE_SECRET_ACCESS_KEY` — private S3-compatible storage.
- `STORAGE_SIGNED_URL_TTL_SECONDS` — short-lived evidence URL expiry (default 120).
- `MAX_EVIDENCE_UPLOAD_BYTES` — configured upload cap (default 10 MiB). The raw-body endpoint's Django `DATA_UPLOAD_MAX_MEMORY_SIZE` is derived as this value plus 1 MiB; the evidence service still enforces the configured cap.
- `ALLOWED_EVIDENCE_CONTENT_TYPES` — comma-separated allowed image MIME types; defaults to JPEG, PNG and WebP.
- `LOCAL_STORAGE_DIR` — private local evidence directory when `STORAGE_MODE=local`. Relative paths resolve from `apps/api`.
- `PUBLIC_BASE_URL` — public API origin used where absolute URLs are needed.
- `ORG_TIMEZONE` — initial IANA timezone for a new organization.
- `MAX_CAPTURE_TIME_DRIFT_SECONDS` — initial non-location evidence-integrity threshold; admins can change the persisted setting in the UI. `DEFAULT_GEOFENCE_RADIUS_M`, `MAX_ACCEPTABLE_GPS_ACCURACY_M` and `MAX_LOCATION_AGE_SECONDS` remain legacy seed values in the schema but no longer affect submissions or review.
- `LOG_LEVEL` — structured application log level. No metrics/APM exporter is bundled.
- First-admin bootstrap uses the CLI, not a startup env user:
  `python manage.py create_admin --email ops@example.org --password-env INITIAL_ADMIN_PASSWORD_ENV`.
  The password is read from that env var or an interactive prompt and is never passed on the command line or logged.

## Web (build-time, public)
- `VITE_API_BASE_URL` — public API path/origin; the default `/api/v1` keeps the same-origin proxy and first-party session cookie.
- `VITE_MAP_STYLE_URL` — optional public MapLibre style URL/key with provider restrictions only. Empty uses the built-in OpenStreetMap streets + Esri satellite basemaps. When set, it takes precedence over both raster tile templates and hides the built-in Map/Satellite switch.
- `VITE_MAP_TILE_URL` — optional public street raster tile template (for example `https://tiles.example.org/{z}/{x}/{y}.png`) used when no full style URL is set. Defaults to the OpenStreetMap tile server, which is suitable for development/small-scale use only; production must use a provider or self-hosted tiles that permit the expected volume.
- `VITE_MAP_SATELLITE_TILE_URL` — optional public satellite raster tile template used by the built-in Satellite layer. Defaults to the public Esri World Imagery service; a production deployment must confirm Esri licensing or point this at a licensed/self-hosted imagery provider.
- No Google Maps API key is required. The UI opens exact coordinates in Google Maps via ordinary links; embedding Google Maps itself is not part of this build.

## Rules
- Vite variables are compiled into browser code; never put a database URL, storage secret, Django secret, SMTP password, or private API secret under `VITE_`.
- Do not commit real values, actual addresses, real site coordinates, real photos, or credentials.
- Production startup rejects a sample/short `SECRET_KEY`, insecure cookie settings, wildcard CORS with credentials, and non-S3/missing storage configuration. Operators must still verify `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` for the deployed origin.
- The documented local workflow uses native PostgreSQL plus Django and Vite; no container runtime is required.
