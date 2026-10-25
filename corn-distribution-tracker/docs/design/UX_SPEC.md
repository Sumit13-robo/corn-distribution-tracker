# UX Specification

## Product personality
Trustworthy, calm, operational and field-friendly. The app is for accountable logistics, not a consumer social product. Use a restrained agricultural palette, strong typographic hierarchy, real whitespace, compact but legible tables, and purposeful imagery. Avoid giant gradients, glassmorphism, gratuitous animation, fake KPIs, and overly playful illustrations.

## Information architecture
### Admin navigation
- **Monitor:** Overview, Distribution map
- **Plan:** Campaigns, Distributors
- Sites are configured inside a campaign (during setup or from the selected campaign panel), not as a separate navigation item.
- **Operate:** Inventory & ledger, Evidence review
- **Oversee:** Analytics & exports, Settings, Audit trail

### Distributor navigation
- **Field work:** Overview, My sites, My submissions, Drafts & sync
- New delivery update is a contextual action from a site, not a separate navigation item.
- There is no Profile/Help screen in this build; account actions live in the top bar.

Do not show admin links to distributors. Route guards are not a security boundary; server permissions must align.

## Admin overview
Top-level metric row: Central on hand, Held by distributors, Approved delivered, Pending review, Remaining target, Flagged records. Every metric includes a unit/definition and the page states that quantities are in kilograms. Below: overall delivery progress (approved against target), pending review queue with flags, distributor performance and recent audit events. The overview is global (no campaign/date filter in the UI); drill-down links open the relevant filtered screen. There is no map preview on the overview.

## Map
Delivery map with a campaign filter and a synchronized list of delivery records. MapLibre plots only the locations distributors captured with `SUBMITTED` or `APPROVED` deliveries on OpenStreetMap streets by default, with a Map/Satellite switch for Esri World Imagery. Site reference coordinates, sites without deliveries, rejected/cancelled claims and the admin's current position are not plotted. A configured `VITE_MAP_STYLE_URL` can point at another provider and hides the built-in switch; a labelled coordinate board is used if the map cannot initialize. Status is shown by colour plus a text badge (approved vs awaiting review). Selecting a delivery opens a drawer with site, distributor, quantity, submitted time, captured coordinates/accuracy, OpenStreetMap/Google Maps links for exact verification and an evidence-review link. Clustering, status/distributor/date filters and a latest-evidence preview are not implemented. The page is list-first on mobile.

## Distributor overview
Simple cards for available stock, remaining target, pending review, approved deliveries and local drafts/queue. Primary action: **Update a site**. Assigned sites show code/name, target/approved/pending/remaining, over-target and due date when set, with a progress bar. No charts and no distance display on this page.

## Delivery form
Short sections: site context → photo evidence → location → quantity and notes → review and submit. Show permission rationale before opening the browser location prompt. Show whether a fix was captured, its coordinates/accuracy and timestamp. Do not show distance, geofence or location-quality warnings: a delivery can be approved from any recorded place. If the page is not served in a secure context, explain that location capture needs HTTPS instead of reporting a misleading permission denial. A resumed draft with a saved fix must keep showing that fix; submitting without re-capturing preserves the saved fix. Quantity unit is explicit; the kg preview is shown, and BAG requires a configured `kg_per_bag` factor. Disable duplicate double-click submissions and show progress. Provide a confirmation summary and the server-confirmed submission reference. The form auto-saves a user-scoped draft with a persistent idempotency key.

## Photo review
Single-record workspace with a large private image, structured metadata, location capture status and review history. Approve (with optional note; an exception reason is required only for non-location evidence integrity or an exceeded target), reject with a required reason, or cancel a pending record; confirm when the action posts stock. The reported fix is plotted on a street/satellite map; the site marker appears only when the site has reference coordinates. Location is labelled Captured or Missing and never blocks approval; distance/geofence warnings are not shown. Previous/next review navigation is not implemented. Keep the original image private and display its capture/source context.

## Tables and forms
- Where present: search, filters, pagination, column headings, empty state with next action, inline validation and clear required indicators. Several current tables omit pagination controls and sort only the loaded page.
- Keep filters in URL where valuable for shareable/reloadable admin views. Current screens keep most filter state in component state; evidence review uses URL query parameters for its scope.
- Display quantities in one consistent unit per view; make conversion clear.
- Use formatted dates/timezone explicitly. For UTC timestamps, render in configured organization/campaign timezone and label if ambiguity exists.
- Destructive actions require confirmation and show effect; stock adjustments require reason and summary.

## Responsive behavior
- Admin desktop: persistent sidebar, top bar with account controls, content panels and tables.
- Admin tablet/mobile: collapsible navigation, cards instead of overflowing dense tables, map switches to list-first mode.
- Distributor mobile: one-column layout, large touch targets (at least about 44×44 CSS px), sticky primary action only where it does not hide form content, safe bottom spacing, camera/location permission feedback and retry UI.

## States and accessibility
Every async page supports loading skeleton/spinner that does not shift the whole page, empty state, recoverable error and retry, permission denied, unauthorized redirect, offline status, and success confirmation. Use semantic headings, labels, focus states, keyboard controls, reduced-motion preferences, sufficient contrast, accessible dialogs, and text/icon status indicators.

## Current scope notes
- Campaign list has a status filter; evidence and audit expose only the filters visible on their screens. Campaign setup contains the site list and optional site-location editing.
- Several admin tables fetch a bounded first page (25 or 100 rows) and sort client-side; they do not expose pagination controls even though the API supports `limit`/`offset`.
- Analytics filters are campaign and UTC date range only; status/distributor/site filters are not in the UI.
- Audit UI filters by action and UTC date range; actor/target filters exist in the API.
- There are no in-app notifications, no Profile/Help page, no thumbnails and no automatic evidence-retention controls in the UI.
