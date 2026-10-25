# File Handoff: `apps/web/src/features/admin/campaigns/CampaignsPage.tsx`

**Status:** TESTED
**Primary owner:** Frontend
**File purpose:** Campaigns and targets UI

## Responsibility
List/create/edit campaigns and plan assignments/targets, clearly showing units and warnings when target/allocation conflicts with available stock.

## Contract and dependencies
campaign/assignment/inventory APIs

Read the relevant contract in `architecture/` or `design/` before implementing. Preserve the APIs, enum values, permission rules, quantity semantics and state transitions established in those documents. Do not create a parallel implementation of the same domain rule in another layer.

## Implementation requirements
- Implement the file fully; do not leave placeholder bodies for required behavior.
- Keep concerns local to this module and expose a narrow, typed interface to dependent modules.
- Validate untrusted input at the appropriate boundary and return/report useful safe errors.
- Consider authorization scope, concurrency, duplicate requests, accessibility and recoverable failure states where applicable.
- Add or update adjacent tests for important success and failure cases.
- Do not use production personal data, real credentials, real geotagged images or hardcoded demo metrics.

## Acceptance criteria
- Validations and server conflict messages are handled.
- The file builds and is integrated with its stated dependencies.
- The behavior matches the source-of-truth docs and is covered by tests where the behavior is non-trivial.

## Handoff back to integrator
When done, report: exported interfaces/endpoints; other files changed; test commands and actual results; environment/config requirements; known limitations; and whether the `file_map.md` status should move to `IMPLEMENTED` or `TESTED`. Only mark `TESTED` when tests were actually run and passed.

## Implementation summary

Campaign create/edit with status filter and assignment/target planning in kg, including date validation and advisory stock warnings. Assignments do not reserve stock; allocation and delivery submission are where balances are enforced. There is no campaign search.

### Campaign-scoped sites (2026-10-25)

The campaign create dialog accepts optional site names, one per line; names are trimmed, case-insensitively de-duplicated and sent as `sites` for transactional campaign creation. After a save the new campaign is selected. The selected campaign shows a **Sites for this campaign** panel with:

- the campaign's active sites, each showing whether a reference location exists;
- a name-only add form (`name` + `campaign_id`, no coordinates);
- an optional location dialog that PATCHes latitude/longitude with numeric range checks and explains that coordinates are optional map context only; existing submissions are not recalculated;
- assignment site options restricted to the selected campaign, showing names only (the generated site code remains internal).

The standalone Sites page and sidebar link were removed; `/sites` redirects to `/campaigns`. The assigned site selector resets when the selected campaign changes. Site mutations invalidate site and overview queries; location changes also invalidate map sites. After a save, the status filter is cleared so the selected campaign/site panel remains visible; campaign and location dialogs reset stale mutation errors when reopened, and switching campaigns clears site/assignment errors.

**Verification (2026-10-25):** `npm test` → 37 passed across 6 files, including three new `CampaignsPage` tests (campaign-dialog names, name-only add, optional location later); `npm run typecheck`, `npm run lint` and `npm run build` pass. `make test-e2e` → 8 passed.

**Unresolved issues:** Clearing a site location is supported by the API but not exposed in this UI. No map picker; coordinates are entered manually.

## Location-warning removal (2026-10-25)

The optional-location dialog no longer promises distance/geofence checks. Coordinates are map context only; a name-only site remains valid and assignable. Verification: `npm test` → 37 passed across 6 files; typecheck/lint/build pass.
