# File Handoff: `apps/api/tests/test_campaign_sites.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Campaign-scoped site creation and optional-location tests

## Responsibility

Cover the campaign setup contract and the campaign/site boundaries:

- campaign creation with optional site names, case-insensitive de-duplication and generated unique site codes;
- name-only site creation inside a campaign and duplicate-name rejection, including a rename to an existing name;
- optional location added later, partial coordinates rejected, and location cleared by sending both coordinates as null;
- the same site name allowed in another campaign with a different generated code;
- assignment rejection when a campaign-scoped site belongs to a different campaign;
- analytics site/map scoping: selecting a campaign excludes another campaign's site, and the map omits a name-only site that site analytics still lists.

## Contract and dependencies

Uses the shared `AuthClient` and `json_request` helpers against real PostgreSQL; all names/coordinates are synthetic.

## Verification

`make test-api` → 98 passed (this file adds 4 tests). `make lint-api` and `make typecheck-api` pass.

## Unresolved issues

None known.
