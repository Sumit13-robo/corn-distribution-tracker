# Geo-tagged Photo Evidence Contract

## User-facing intent
A distributor submits a site report with a photo and the device's location so an admin can review whether the report is consistent with the assigned site and time. The application must describe this as **evidence with quality indicators**, not guaranteed proof that the corn was physically delivered.

## Capture requirements
- Request browser geolocation only after an intentional user action in the report flow. Use `enableHighAccuracy` when supported and a bounded timeout; show coordinates/accuracy and a retry action.
- Record reported horizontal accuracy in metres and the device location timestamp when provided. Reject invalid coordinates; flag stale readings and readings whose accuracy exceeds the configured threshold.
- Prefer a fresh camera capture through browser camera APIs or mobile capture input. If the browser only offers file selection, label the capture source honestly. Never silently label a gallery upload as a fresh camera photo.
- Capture a client timestamp and always record server receipt timestamp independently. Client time is advisory and can be changed.
- The image file gets a SHA-256 content hash. Hash proves byte identity only, not when/where it was captured or whether its content is true.

## Site comparison
- Each site has expected WGS84 coordinates and configurable `geofence_radius_m` and `max_acceptable_accuracy_m`.
- Calculate distance server-side using the reviewed geodesic implementation in `corn.geo` (Vincenty inverse on WGS84 with a haversine fallback), not an untested planar degree calculation. PostGIS is not used in this build.
- Produce flags such as `GPS_MISSING`, `GPS_STALE`, `GPS_LOW_ACCURACY`, `OUTSIDE_GEOFENCE`, `EXIF_GPS_MISMATCH`, `CAPTURE_TIME_MISMATCH`, `DUPLICATE_IMAGE_HASH`, `UNEXPECTED_FILE_TYPE`, and `LOCATION_EXCEPTION` as applicable.
- Define exact threshold semantics in config and show the values to reviewers; avoid a hidden universal threshold.
- If GPS is unavailable or outside radius, the system may allow a submission only under the configured exception policy. It must visibly mark it for admin review; no silent bypass.

## Metadata and storage
- Do not rely only on client-posted fields. Validate image by decoding it, checking actual size/type, calculating hash server-side and optionally reading EXIF server-side with a maintained library.
- EXIF may be absent because mobile browsers can strip it. Missing EXIF should be a flag/informational state, not automatic evidence of fraud unless policy explicitly says so.
- Preserve original in a private bucket, store opaque random object keys, and use signed URLs for authorized viewing. If creating thumbnails, strip location EXIF from the derivative while retaining structured original metadata in access-controlled evidence data.
- Upload intent should expire, be bound to an authenticated user and expected constraints, and be consumed once. Clean up unassociated uploads by a documented job/process.
- Store evidence lifecycle, uploader, file metadata, hash, capture metadata, server timestamps, site location/distance, and review decisions. Keep review/exception history audit logged.

## Admin review UI
Show image + site name/code + distributor + submitted time + quantity + expected site point + captured point + distance + reported accuracy + capture source + EXIF comparison if available + hash/duplicate status + flags + prior site reports. Use textual labels/icons as well as colors. Reviewers can open full image with an expiring URL. For off-site or low-confidence cases, an override requires a reason and creates an audit event.

## Limits and anti-fraud honesty
- Browser geolocation can be spoofed, simulated or inaccurate.
- A file can be edited before upload; a content hash does not prove its creation time or scene.
- EXIF data can be absent or manipulated.
- A web app cannot cryptographically attest that corn was delivered without additional trusted hardware/process controls.

Design for traceability, cross-checks, review and deterrence. Do not claim fraud is impossible or that a GPS pin alone validates a delivery.
