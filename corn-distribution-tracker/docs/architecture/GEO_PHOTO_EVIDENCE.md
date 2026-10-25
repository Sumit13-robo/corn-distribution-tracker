# Geo-tagged Photo Evidence Contract

## User-facing intent
A distributor submits a site report with a photo and, when available, the device's location so an admin can review the report alongside the assigned site, time and evidence integrity checks. Location is supporting metadata, not an approval gate: **any submission with a recorded place can be approved from that place.** The application must describe this as **evidence with quality indicators**, not guaranteed proof that corn was physically delivered.

## Capture requirements
- Request browser geolocation only after an intentional user action in the report flow. Use `enableHighAccuracy` when supported and a bounded timeout; show coordinates/accuracy and a retry action.
- Record reported horizontal accuracy in metres and the device location timestamp when provided. Reject malformed or out-of-range coordinates; accepting a submission without a fix is allowed.
- Location accuracy, fix age, geofence distance and missing coordinates must **not** produce warning flags, block submission or require a review exception.
- Prefer a fresh camera capture through browser camera APIs or mobile capture input. If the browser only offers file selection, label the capture source honestly. Never silently label a gallery upload as a fresh camera photo.
- Capture a client timestamp and always record server receipt timestamp independently. Client time is advisory and can be changed.
- The image file gets a SHA-256 content hash. Hash proves byte identity only, not when/where it was captured or whether its content is true.

## Site comparison
- A site may have an optional WGS84 reference point. A site may also be name-only with no coordinates. Never invent coordinates or recalculate historical records.
- Calculate distance server-side using the reviewed geodesic implementation in `corn.geo` (Vincenty inverse on WGS84 with a haversine fallback) only when both the captured fix and the site reference exist. PostGIS is not used in this build.
- `distance_to_site_m` is informational review context. It is `null` for a name-only site or a submission without a fix. It is not a delivery-map marker, never creates `OUTSIDE_GEOFENCE`, never blocks approval and never requires an exception.
- Legacy site fields (`geofence_radius_m`, `max_acceptable_accuracy_m`) and legacy settings remain in the schema for compatibility but are no longer evaluated or exposed as review controls.
- Historical records may contain old location flags such as `GPS_MISSING`, `GPS_STALE`, `GPS_LOW_ACCURACY`, `OUTSIDE_GEOFENCE`, `EXIF_GPS_MISMATCH` or `LOCATION_EXCEPTION`. They remain readable for audit history, but the current UI filters them from warnings and they never gate approval.
- New records use `geo_status` `PASS` when a fix was captured and `UNAVAILABLE` when it was not. `WARNING`/`EXCEPTION` are legacy values only.

## Evidence-integrity flags
- Generate and review only non-location integrity signals: `CAPTURE_TIME_MISMATCH`, `DUPLICATE_IMAGE_HASH` and `UNEXPECTED_FILE_TYPE`.
- EXIF GPS/time may be extracted and stored as metadata. An EXIF-vs-reported distance may be retained for audit context, but it must not emit a location warning. Missing EXIF is an informational state, not automatic evidence of fraud.
- These non-location integrity flags may require an explicit override reason before approval; location never does. Approvals remain manual and are always audit logged.

## Metadata and storage
- Do not rely only on client-posted fields. Validate image by decoding it, checking actual size/type, calculating hash server-side and optionally reading EXIF server-side with a maintained library.
- EXIF may be absent because mobile browsers can strip it. Missing EXIF should be recorded as an informational state, not automatic evidence of fraud unless policy explicitly says so.
- Preserve original in a private bucket, store opaque random object keys, and use signed URLs for authorized viewing. If creating thumbnails, strip location EXIF from the derivative while retaining structured original metadata in access-controlled evidence data.
- Upload intent should expire, be bound to an authenticated user and expected constraints, and be consumed once. Clean up unassociated uploads by a documented job/process.
- Store evidence lifecycle, uploader, file metadata, hash, capture metadata, server timestamps, optional site/location context, and review decisions. Keep review/exception history audit logged.

## Admin review UI
Show image + site name/code + distributor + submitted time + quantity + captured point (or **Missing**) + optional expected site point + reported accuracy + capture source + hash/duplicate status + non-location evidence-integrity flags + prior site reports. Use textual labels/icons as well as colours. Reviewers can open the full image with an expiring URL.

- Do not show distance, geofence radius, GPS quality warnings or "outside geofence" copy.
- Label a fix as **Captured** or **Missing**; neither is a warning and neither blocks approval.
- An override reason is required only for a non-location evidence-integrity flag or an exceeded assignment target. A location exception is not part of the policy.
- Historical location flags are not surfaced as review warnings.

## Limits and anti-fraud honesty
- Browser geolocation can be spoofed, simulated or inaccurate.
- A file can be edited before upload; a content hash does not prove its creation time or scene.
- EXIF data can be absent or manipulated.
- A web app cannot cryptographically attest that corn was delivered without additional trusted hardware/process controls.

Design for traceability, cross-checks, manual review and deterrence. Do not claim fraud is impossible, that a GPS pin alone validates a delivery, or that location is a gate.
