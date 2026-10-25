# Screen-by-Screen Specification

This document describes the screens in the current build. Where a feature is absent, it is called out rather than specified as if implemented.

## Public/auth
### Login
Branded shell with email/password, show/hide password, inline validation, generic auth failure, pending/loading state, reset-password link, and responsive layout. No public registration. Role redirects after `/auth/me` using the server-resolved role. A `429` shows the server retry window; credential failures stay generic.

### Password help / reset / invitation / change
One focused screen with four modes:
- `forgot`: records a reset request for an operator; no mail is sent.
- `reset`: one-time token + new password.
- `invite`: one-time invitation token + display name + initial password.
- `change`: signed-in password change with current password.

Tokens are single-use and expiring. Results never reveal whether an account exists.

## Admin
### Overview
KPI row: central on hand, held by distributors, approved delivered, pending review, remaining target, flagged records. Below: overall delivery progress, pending review queue with non-location evidence-integrity flags, distributor performance and recent audit events. The flagged count excludes location quality. Drill-down links open filtered views. There is no campaign/date filter, map preview or per-campaign progress block on this screen.

### Distribution map
Delivery map with a campaign filter and a synchronized delivery list. MapLibre renders only distributor-recorded locations tied to `SUBMITTED` or `APPROVED` delivery records on OpenStreetMap streets by default; a Map/Satellite switch shows Esri World Imagery. Site reference coordinates are never plotted, so sites without deliveries/coordinates contribute nothing and there is no “My location” admin marker. `VITE_MAP_STYLE_URL` selects a different public style and hides the built-in switch; `VITE_MAP_TILE_URL` and `VITE_MAP_SATELLITE_TILE_URL` override the raster templates. A labelled coordinate board is the fallback when the map cannot initialize. The legend distinguishes approved delivery from delivery awaiting review. Selecting a delivery opens a drawer with site/distributor, quantity, submitted time, captured coordinates/accuracy, exact OpenStreetMap/Google Maps links and a link to evidence review. Rejected/cancelled claims are excluded. Clustering, status/distributor/date filters and a latest-evidence preview are not implemented. Server returns only records visible to the current admin scope; no evidence URLs are exposed.

### Campaigns and targets
Campaign list with a status filter, create/edit form (name, reference, dates, timezone, status, notes), and a campaign-scoped site/assignment planner. The create form accepts optional site names, one per line; sites are created with the campaign in one transaction. Selecting a campaign opens a **Sites for this campaign** panel where an admin can add another name-only site and optionally set or edit its latitude/longitude later. Site codes are generated server-side when omitted, duplicate names within a campaign are rejected, and a site location can be cleared by sending both coordinates as null. Name-only sites remain usable for assignments. A site location is optional evidence-review context only; it is not a delivery map marker, and distance/geofence never gate review. The assignment planner only offers sites from the selected campaign and compares proposed targets against available stock, showing advisory warnings only; assignments do not reserve stock or reject a target solely because it exceeds current stock. Stock allocations and delivery submissions are validated against ledger balances. There is no standalone Sites page, site search, map picker, campaign search or campaign-level progress chart.

### Distributors
Searchable list with status, held/available stock, open assignments, invite state and last login. Admin can invite a new distributor, rename one, or deactivate one. The raw invitation link is shown once for secure delivery. Re-invite and password reset from this list are not implemented; passwords are never shown or reset here.

### Inventory and ledger
Balances by account, reconciliation status, receipt/allocation/adjustment forms, and movement history with reversal. Receipts require a source reference; adjustments require a reason and confirmation. Forms post kilograms only. There is no manually editable balance field and no CSV export on this screen.

### Evidence review
Pending queue with site/distributor/quantity/age/flags; URL query parameters support site and distributor scoping. Detail shows the private image(s), coordinates, accuracy, timestamps, non-location evidence-integrity flags and review history, plus a street/satellite map of the distributor-reported fix and, when the site has coordinates, the site's current location, with OpenStreetMap and Google Maps links. Location is labelled Captured or Missing; there is no distance card, geofence warning or location exception. For a name-only site the site marker is omitted and the site location is simply absent. Approve (optional note; exception reason only for evidence integrity or an exceeded target), reject with required reason, or cancel a pending record. No previous/next navigation.

### Analytics and exports
Campaign and UTC date-range filters, scope metrics, distributor/site bar+table breakdowns, and an audited CSV export using the same campaign/date filters. No status/distributor/site filters and no URL-persisted filter state.

### Settings
Organization timezone, default display unit, kg-per-bag factor and capture-time drift. Every change is audit-logged. Legacy geofence/accuracy/location-age fields remain in the API/schema but are not editable and do not affect review. Storage/retention are deployment-level settings and are not editable here.

### Audit trail
Append-only event list with action and UTC date-range filters, actor/target context and details. Actor/target filters exist in the API but are not exposed in the current UI.

## Distributor
### Overview
Cards: available stock, remaining target, pending review, approved quantity and local drafts/queue. Primary action “Update a site”; assigned sites show code/name, target/approved/pending/remaining, over-target and due date, with progress bars. There is no distance display or chart.

### Assigned sites
Search by code/name/region over the signed-in distributor's own assignments. Each item shows code/name, target, approved, pending, remaining, site address, due date, and links to site detail or a new delivery.

### Site detail
Site-location panel with coordinates (no tile map) when the site has a reference point; a name-only site states that no reference location has been set but device fixes are still stored. Also shows assignment target/progress and the distributor's own previous submissions with status, quantity, captured/missing location and review reason. CTA to create a new update. Other distributors' records are never exposed.

### Delivery update
Sections: site context → photo evidence → location → quantity/notes → review and submit. Photo capture is required before submit; location is optional and never blocks or warns. Show Captured/Missing plus coordinates/accuracy when present. Quantity unit is explicit (kg/quintal/tonne/bag) with a kg preview; bag requires a configured factor. The draft auto-saves with a persistent idempotency key; offline submissions stay `QUEUED` until the server acknowledges them. If the page is served over insecure HTTP, location capture explains that HTTPS is required; camera/file selection still works. A resumed draft with a saved fix displays that fix and does not show a location warning.

### My submissions
List of the signed-in distributor's records with status filter, quantity, state, evidence status and review reason. Expanding a row shows the full submission context.

### Submission history/detail
Delivered as expanding rows in My submissions and as a history list on site detail. Shows status, review reason, non-location evidence-integrity flags, timestamps and evidence status. Location is shown as captured/missing, not as a warning. Rejected items are context for a new submission, not editable in place.

### Drafts & sync
Local drafts with last-saved time, queue/upload/error state, retry, sync-all, discard confirmation and sync result. Local-only records are unmistakably labelled; photos remain in IndexedDB where available.
