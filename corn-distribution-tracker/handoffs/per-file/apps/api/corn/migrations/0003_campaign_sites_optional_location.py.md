# File Handoff: `apps/api/corn/migrations/0003_campaign_sites_optional_location.py`

**Status:** TESTED
**Primary owner:** Backend
**File purpose:** Add campaign-scoped sites with optional coordinates and backfill existing sites

## Responsibility

Add `DistributionSite.campaign` as a nullable FK (legacy/global rows remain possible), make `latitude`/`longitude` nullable, and backfill each existing site from the campaign of its earliest assignment. The migration does not invent coordinates or rewrite records.

## Contract and dependencies

- Depends on `corn.0002_append_only_triggers`.
- Backfill uses only `DistributorAssignment.campaign_id` values; sites with no campaign assignment remain null.
- Reversal is a no-op for the data backfill (Django cannot safely restore the prior null/non-null distribution).
- Applied to the development database on 2026-10-25; `makemigrations --check --dry-run` reports no changes.

## Verification

`make migrate` → applied `corn.0003_campaign_sites_optional_location`; existing `GUDELE-02` and `MUNUKI-01` sites are attached to `Juba Central 2026`. `make test-api` → 98 passed, including campaign-site creation, optional/cleared location, duplicate-name and cross-campaign assignment tests. `make lint-api` and `make typecheck-api` pass.

## Unresolved issues

None known. Sites with no assignment campaign remain global/nullable by design; the current UI always creates sites inside a campaign.
