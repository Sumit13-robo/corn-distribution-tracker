# File Handoff: `infra/railway-bucket-cors.json`

**Status:** IMPLEMENTED
**Primary owner:** DevOps
**File purpose:** S3 CORS policy for browser presigned evidence uploads.

## Current implementation

Allows `PUT`, `GET` and `HEAD` from the Vercel production origin, permits the
content-type and SSE/KMS headers used by upload intents, and exposes `ETag`.
The origin is a placeholder that must be replaced before applying.

## Verification

- `python3 -m json.tool infra/railway-bucket-cors.json` → valid JSON.
- Not applied to a real Railway Bucket; provider CORS behavior remains external.

## Unresolved issues

Confirm the provider's CORS UI/API accepts this policy and test a real browser
PUT before launch.
