# Environment Variables

Use `.env.example` with safe placeholders only. Validate required values at API startup and fail fast for missing or insecure production settings. Keep `.env` out of source control.

## API
- `APP_ENV` — `development|test|staging|production`.
- `APP_NAME` — display/service name.
- `API_V1_PREFIX` — normally `/api/v1`.
- `DATABASE_URL` — PostgreSQL connection string, with credentials from secret manager in production.
- `SECRET_KEY` / token signing key — high-entropy secret from secret manager; never use a sample default in production.
- `ACCESS_TOKEN_TTL_MINUTES` — short access lifetime.
- `REFRESH_TOKEN_TTL_DAYS` — explicit refresh lifetime with rotation/revocation.
- `CORS_ALLOWED_ORIGINS` — comma-separated exact origins; never wildcard with credentials.
- `COOKIE_SECURE`, `COOKIE_SAMESITE`, `COOKIE_DOMAIN` — production-safe cookie settings; document CSRF/Origin requirements.
- `RATE_LIMIT_BACKEND_URL` — optional shared backend for distributed rate limiting.
- `STORAGE_ENDPOINT_URL`, `STORAGE_REGION`, `STORAGE_BUCKET`, `STORAGE_ACCESS_KEY_ID`, `STORAGE_SECRET_ACCESS_KEY` — private S3-compatible storage.
- `STORAGE_SIGNED_URL_TTL_SECONDS` — short-lived signed URL expiry.
- `MAX_EVIDENCE_UPLOAD_BYTES` — configured limit.
- `MAP_TILE_STYLE_URL` / public map provider settings — public key only if provider explicitly supports safe browser use; set domain restrictions at provider.
- `ORG_TIMEZONE` — explicit IANA timezone.
- `DEFAULT_GEOFENCE_RADIUS_M`, `MAX_ACCEPTABLE_GPS_ACCURACY_M`, `MAX_LOCATION_AGE_SECONDS` — documented evidence thresholds.
- `LOG_LEVEL` — API application log level. No metrics/APM exporter or alerting integration is bundled; see the launch risks in the README.
- `INITIAL_ADMIN_EMAIL` should only be used by a controlled one-shot bootstrap tool, not as an automatic public startup user; avoid password env var where secure interactive prompt is possible.

## Web
- `VITE_API_BASE_URL` — public API origin/path only.
- `VITE_MAP_STYLE_URL` — public map style URL/key with provider restrictions only.

## Rules
- Vite variables are compiled into browser code; never put DB, storage secret, signing key, SMTP password, or private API secret under `VITE_`.
- Do not commit real values, actual addresses, real site coordinates, real photos, or credentials.
- Production startup must reject insecure secrets, public storage configuration when detectable, and unsafe CORS/cookie combinations.
