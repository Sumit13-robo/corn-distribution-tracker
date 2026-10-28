# File Handoff: `apps/api/tests/test_geotag_validation.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Location capture, no-warning behavior and non-location evidence-integrity tests

## Current implementation

Covers direct `evaluate_geo` and submission/review behavior:

- valid coordinates and geodesic distance when both a fix and site reference exist;
- missing, stale, inaccurate and far-away fixes produce `geo_flags == []`, with `geo_status` `PASS` or `UNAVAILABLE` and no approval exception;
- name-only sites keep a null distance while still storing the device fix;
- EXIF GPS difference is stored as metadata without an `EXIF_GPS_MISMATCH` warning;
- invalid coordinate ranges are still rejected;
- duplicate image hash, capture-time mismatch and unexpected file type remain evidence-integrity warning tests.

## Verification

`make test-api` → 98 passed; `make lint-api` clean; `make typecheck-api` clean in 51 source files; migration check no changes. `make test-e2e` → 9 passed.

## Unresolved issues

None known.
