# File Handoff: `apps/api/corn/geo.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Geodesic distance and captured-location metadata; no location warnings or approval gate

## Current implementation

- `validate_coordinates` rejects latitude/longitude outside WGS84 ranges.
- `geodesic_distance_m` uses Vincenty inverse on WGS84 with a haversine fallback for non-convergent/antipodal pairs.
- `evaluate_geo` accepts legacy thresholds but deliberately does not evaluate them. It returns `distance_m` only when both a device fix and a site reference exist, an empty `flags` list and `geo_status` `PASS` (fix) or `UNAVAILABLE` (no fix).
- No `GPS_MISSING`, `GPS_STALE`, `GPS_LOW_ACCURACY`, `OUTSIDE_GEOFENCE` or `EXIF_GPS_MISMATCH` is generated. Location never blocks approval or requires an exception.

## Verification

`make test-api` → 98 passed; `make lint-api` → all checks passed; `make typecheck-api` → no issues in 51 source files; migration check → no changes. `test_geotag_validation` covers missing, stale, inaccurate and far-away fixes, including direct `evaluate_geo` and submission-level approval without a location exception.

## Unresolved issues

None known. Historical location flags remain readable in stored JSON but are not produced or displayed as warnings.
