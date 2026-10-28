# Railway + Vercel Deployment

Topology: Railway runs Django/DRF, PostgreSQL and a private S3-compatible
bucket. Vercel serves the Vite SPA and proxies `/api/*` to Railway. The browser
only talks to the Vercel origin, so the HttpOnly session cookie stays
first-party and no cross-site cookie mode is required.

## 1. Railway backend

1. Create a Railway project and add **PostgreSQL** and **Bucket** services.
2. Create a service from this repository with **Root Directory**
   `corn-distribution-tracker/apps/api`. Railway reads `railway.json`:
   Dockerfile build, `preDeployCommand` migration, `sh bin/start.sh`, and
   `/health/ready` healthcheck.
3. Copy `apps/api/.env.railway.example` into the service variables and replace
   every placeholder. Generate the secret with `openssl rand -hex 48`. If your
   Railway services are not named `Postgres` and `Bucket`, update those two
   variable-reference prefixes.
4. Generate a public domain for the API. Set `ALLOWED_HOSTS` and
   `PUBLIC_BASE_URL` to that host/URL. Include `localhost,127.0.0.1` if you
   want the image's Docker healthcheck to pass as well as Railway's probe.
   `RAILWAY_PUBLIC_DOMAIN`, `RAILWAY_PRIVATE_DOMAIN` and
   `healthcheck.railway.app` (when Railway hostnames are present) are added
   automatically.
5. Set `FRONTEND_ORIGIN` to the final Vercel production origin. It is added to
   CORS and CSRF automatically. If the Vercel URL is not known yet, deploy the
   backend once with the placeholder, deploy Vercel, then update this value and
   redeploy the backend. Deploy the backend after the value is set.
6. Apply the bucket CORS policy from `infra/railway-bucket-cors.json`. Replace
   the placeholder origin with the Vercel production origin. The policy allows
   the presigned browser `PUT` and the SSE headers used by the API. If you use
   the AWS CLI against the bucket endpoint:

   ```bash
   aws s3api put-bucket-cors \
     --endpoint-url "$STORAGE_ENDPOINT_URL" \
     --bucket "$STORAGE_BUCKET" \
     --cors-configuration file://infra/railway-bucket-cors.json
   ```
7. For a Railway Bucket set `STORAGE_SERVER_SIDE_ENCRYPTION=` (empty) and
   `STORAGE_ADDRESSING_STYLE=virtual`: the bucket is encrypted at rest but does
   not support the S3 SSE request header, and it uses virtual-hosted URLs. For
   AWS S3/R2/other providers, set the provider's endpoint/region/keys and the
   appropriate SSE/addressing settings.
8. Verify:

   ```bash
   curl -fsS https://YOUR-SERVICE.up.railway.app/health/live
   curl -fsS https://YOUR-SERVICE.up.railway.app/health/ready
   ```

9. Create the first admin through a Railway shell or one-off command. Prefer
   the environment-variable path because a Railway shell may not allocate a
   TTY for `getpass`:

   ```bash
   INITIAL_ADMIN_PASSWORD_ENV='replace-with-a-strong-password' \
     python manage.py create_admin --email ops@example.org
   ```

## 2. Vercel frontend

1. Import this repository into Vercel.
2. Set **Root Directory** to `corn-distribution-tracker/apps/web`.
3. Framework preset: **Vite**. Install `npm ci`; build
   `node scripts/check-deploy-config.mjs && npm run build`; output `dist`.
   The first command fails the Vercel build until the next step is complete.
4. Replace the placeholder in `apps/web/vercel.json`:

   ```text
   https://your-service.up.railway.app
   ```

   with the real Railway public origin. The rewrite `"/api/:path*"` must point
   at the backend; the second rewrite handles SPA deep links.
5. `VITE_API_BASE_URL` can stay unset: the client defaults to `/api/v1` and the
   Vercel rewrite keeps it same-origin. Set the optional `VITE_MAP_*` variables
   only for a production tile/style provider.
6. Deploy. Update the Railway `FRONTEND_ORIGIN` to the resulting production
   Vercel origin and redeploy the backend if it changed.

## 3. Production checks

```bash
curl -fsS https://YOUR-APP.vercel.app/api/v1/health/ready
```

Then verify in a browser: login sets a Secure HttpOnly cookie, an unsafe admin
mutation succeeds with CSRF, a synthetic delivery can request a presigned
upload, the object completes and attaches, and a replaced object is rejected.

## 4. Boundaries

- Vercel preview URLs are not automatically trusted by `CSRF_TRUSTED_ORIGINS`;
  add explicit preview origins only if needed.
- The Vercel rewrite keeps `/api/*` same-origin, but verify `Set-Cookie` and
  `Cookie` round-trips in the target region. If your Vercel plan does not
  preserve them, use custom domains under one registrable domain
  (`app.example.com` and `api.example.com`), set
  `VITE_API_BASE_URL=https://api.example.com/api/v1`, and update
  `ALLOWED_HOSTS`, `FRONTEND_ORIGIN` and the bucket CORS origin.
- The Railway bucket must have CORS configured before browser evidence uploads
  work. Do not enable `TRUST_X_FORWARDED_FOR` until the edge behavior is
  verified; the default keeps source-IP trust off. Behind the Vercel proxy,
  per-IP rate limiting sees the proxy egress unless a verified trusted-header
  setup is added.
- Railway Hobby/free services may sleep; use an always-on plan for a production
  API. Rate limiting remains process-local unless a shared limiter is added.
- This document does not replace the real-provider upload/CORS/KMS drill,
  staging ingress/TLS verification, load/soak tests, or a production restore
  measurement.
