# Screen-by-Screen Specification

## Public/auth
### Login
Clean branded shell with email/password, show/hide password, inline validation, generic auth failure, pending/loading state, reset-password link, and responsive layout. No public registration. Role redirects after `/auth/me` using server-resolved role.

## Admin
### Overview
KPI metric row with definitions; campaign-level progress; small map preview; pending review queue with flags; distributor performance list; recent audit events. Every item links to a properly filtered detail view.

### Distribution map
Full-featured MapLibre map, clustered site markers, campaign/status/distributor/date filters, legend, synchronized site list, accessible point selection, side drawer with quantities and latest evidence. Server returns only sites visible to the current admin scope.

### Campaigns and targets
Searchable list, campaign create/edit, status/date/timezone; target/assignment planner with quantity conversion and validation; warn when proposed assignments exceed central or distributor-available stock. Save allocation and ledger transfer consistently.

### Campaigns and targets
Campaign list/create/edit, status/date/timezone and distributor-site assignment planning with canonical kg and explicit display conversions; warn about stock/target conflicts.

### Sites
Table/list, map pick or coordinate entry, geofence radius/accuracy settings, active/deactivate state, duplicate site-code prevention, location-change audit, site detail with all delivery history.

### Distributors
List, status, assigned campaigns/sites, allocated/available stock, pending and approved totals; invite/re-invite/deactivate, show invite state without exposing token; never show/reset the existing password.

### Inventory and ledger
Current balances by account; receipt/allocation/adjustment forms; movement history with source/destination/type/reference/quantity/actor/time; reconciliation status and export. Adjustment requires review/confirmation and reason. Never present a manually editable balance field.

### Evidence review
Pending queue with site/distributor/quantity/age/flags; evidence detail with private image, location map comparison, accuracy/distance/timestamps/hash/metadata checks/history; approve; reject with required reason; accept geo exception with required reason. Clearly warn that approval posts a stock movement.

### Analytics and exports
Filters at top, visible selected campaign/date range, clear definitions and units, accessible charts plus tables for same data, distributor/site breakdowns, CSV export. No chart with invented values.

### Settings / audit
Organization timezone, default display unit, kg-per-bag config, geolocation quality thresholds, geofence defaults, storage/retention indicators where configurable, user/admin audit view. Protect security-sensitive settings and audit edits.

## Distributor
### Overview
Cards: available stock, assigned target remaining, submitted pending, approved quantity, local drafts/queue. Main action “Update a site”; assigned sites listed with clear progress/status.

### Assigned sites
Search/filter own sites; each item shows site code/name, target, submitted/pending/approved, remaining target, last update and due date if set.

### Site detail
Site address/map/location note, expected pin, assignment target and progress, previous own submissions, CTA to create a new update. Never expose other distributors' private records.

### Delivery update
Site context, capture location, capture camera photo, quantity+unit, notes, evidence warnings, final review and submit. Prevent duplicate clicks and preserve draft. Explain any fallback photo method and show clear permission failure messages.

### My submissions
List only the signed-in distributor's submissions with quantity, state, evidence status and review reason.

### Submission history/detail
Status timeline, submitted quantity, evidence thumbnail/detail, server timestamps, review status/reason, ledger/receipt identifier only when appropriate. Rejected items can be used as context for creating a new submission but are not edited in place after review.

### Drafts & sync
List local drafts with last saved time, queue/upload/error state, retry, discard confirmation and sync result. Local-only records are unmistakably labelled.
