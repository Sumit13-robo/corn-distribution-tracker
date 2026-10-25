# Product Requirements Document

## 1. Problem
Corn quantity is distributed across locations by distributors. The organization needs a common record of available stock, allocations, site-level delivery progress, and photo/location evidence so that supervisors can reconcile physical deliveries and assign accountability.

## 2. Product outcomes
- Know how much corn was received, allocated to each distributor, submitted as delivered, approved as delivered, and remains in stock.
- See every recorded delivery location on a map, with status and quantities, and inspect the linked site’s delivery history.
- Make distributor updates accountable through user identity, time, optional geolocation context, photo hash, evidence integrity checks and manual admin review.
- Identify over/under delivery, pending approvals, missing evidence, duplicate/capture-time integrity issues, low photo coverage, and distributor performance.
- Work reliably on mobile devices in areas with weak connectivity.

### Current implementation status (2026-10-23)
Implemented: session auth/roles, campaigns/sites/assignments, inventory ledger with receipts/allocations/adjustments/reversals, delivery submission with private evidence, review/approval/rejection/cancel, delivery-only admin map (MapLibre + OpenStreetMap streets and Esri satellite by default, configurable provider, Google Maps links, coordinate fallback), analytics/CSV export, settings, audit, offline drafts/sync.

Deferred in the current UI/API: marker clustering, status/distributor/date map filters, overview map preview, previous/next evidence review, location map comparison, image thumbnails, in-app notifications, Profile/Help, re-invite/password reset from the distributor list, unit selectors on inventory forms, distributor/site/status analytics filters, audit actor/target filters, and pagination controls on most tables. See the README known limitations for the full list.

## 3. Roles
### Admin
May manage distributor accounts/invitations, campaigns, sites, assignments/targets, inventory receipts and allocations, evidence review, approvals/rejections, adjustments with reasons, analytics, exports, and organization settings. Every sensitive change creates an audit event.

### Distributor
May view own account context in the top bar, assigned campaigns/sites, own allocated/available stock, site targets, own submissions and review feedback, and create a delivery submission at an assigned site. Cannot create administrators, alter stock directly, approve own submissions, see another distributor's private evidence, or change an approved ledger entry.

## 4. Core entities
- Campaign: a named distribution effort with dates, status, timezone and notes; display-unit and bag conversion settings are organization-wide.
- Site: named physical delivery point with address/description, optional reference latitude/longitude for evidence-review context, and active state. Legacy geofence fields do not gate review.
- Distributor assignment: distributor + campaign + site + target quantity in kg and optional notes.
- Inventory account: central warehouse, distributor stock account, or site stock account.
- Stock movement: append-only transfer/receipt/adjustment with quantity in kg, source/destination, type, actor, time, reference and reversal linkage.
- Distribution record: distributor's submission of quantity and site visit data, status, idempotency key and review history.
- Evidence: private image object plus geo/capture metadata, hash, validation flags, and lifecycle state.
- Audit event: append-only record of important actions with actor, target, time, request correlation ID and non-secret change summary.

## 5. Main requirements
### Inventory
- Register incoming corn receipt with quantity, unit input, reference/source, received time, notes and actor.
- Allocate stock from central warehouse to distributor stock account.
- Track distribution to sites through approved submissions.
- Record spoilage/loss/adjustment/return only using a controlled transaction with reason and audit event.
- Enforce non-negative stock, double-entry-like source/destination movements, concurrency safety and idempotency.
- Convert displayed units consistently; canonical persisted unit is kg. Bag conversion requires an explicit configured kg-per-bag value and shows it to users.

### Site management
- Admin can create/edit/deactivate a site and optionally set reference coordinates for evidence-review context; the admin delivery map never uses them as delivery markers. Quantity targets and distributor assignments are planned on the Campaigns screen.
- Site markers convey status using both color and text/icon. Marker selection shows target, submitted, approved, pending and remaining planned amount, distributor, last visit and evidence status.
- A site can have multiple visits; do not overwrite historic visits with the latest update.

### Distributor workflow
- List assignments with target, completed/approved quantity, quantity pending review, remaining target, available stock and due/status information.
- Open a site, request location permission and display whether a fix was captured plus its accuracy; provide retry guidance but allow submission with or without a fix.
- Capture a fresh photo, enter quantity (unit is explicit), optional note, and submit. Location is optional support metadata: any recorded place can be approved and no distance/geofence/location-quality warning is shown.
- Save a draft when offline, queue retry safely, and distinguish local draft from server-confirmed submission.
- A distributor can see rejection reason and submit a new/corrected report without rewriting previous evidence or a posted ledger movement.

### Admin evidence review
- View all authorized evidence with original timestamp, server timestamp, submitting user, site, coordinates (or Missing), reported accuracy, optional expected coordinates, image hash, duplicate/capture-time warnings, EXIF context when available, and non-location validation flags.
- Approve or reject with optional/required review reason according to the action; approval posts a stock movement atomically. Rejection must not change stock and releases the reserved quantity.
- Admin override of a non-location evidence-integrity warning or an exceeded target requires a reason and is auditable. Location never requires an override.
- Photos load from short-lived signed URLs; no public bucket or permanent public image URL.

### Analytics and exports
- Overview totals: physical stock by account; total received; currently held by distributors; submitted/pending quantity; approved/distributed quantity; remaining assigned target; rejected quantity; open review count; evidence completeness; non-location evidence-integrity flagged submissions.
- Filters: campaign and date range are implemented in the UI; distributor, site, status and region filters are deferred (some are available through API parameters).
- Distributor performance: assigned target, submitted, approved, pending, rejected, stock remaining, on-time visits where due dates exist, evidence quality and exception rate. Make denominators explicit.
- Site performance: target, submitted, approved, pending, remaining target, last visit and evidence coverage.
- CSV exports require permission, filters must match the visible result, large exports should be bounded or generated asynchronously later, and exports must not leak hidden records.

## 6. Non-functional requirements
- Security: secure auth/session management, rate limiting, password hashing, server RBAC, secure headers, strict CORS, private image storage, secret management, safe errors and audit trail.
- Reliability: transactional ledger operations, idempotent mutation endpoints, migrations, backup and tested restore instructions.
- Performance: paginated API lists, indexed filters and bounded responses are implemented; most admin tables do not yet expose pagination controls. Clustered map points and thumbnail derivatives are deferred. Signed URLs are implemented.
- Accessibility: WCAG 2.2 AA intent.
- Mobile: distributor workflow optimized for modern Android/iOS browsers; camera and geolocation permission states handled gracefully.
- Privacy: collect location only during a relevant site update, state why it is collected, protect evidence, and define retention configurable by policy.
- Observability: structured logs without sensitive payloads, request IDs, health/readiness checks, exception monitoring and operational alerts for repeated failures.

## 7. Out of scope for first release
- Native mobile app; use responsive web/PWA.
- Automated face recognition, identity recognition, or covert tracking.
- Claims that GPS, EXIF, image hashes or geofence distance prove a physical delivery occurred. Also out of scope: blocking approval because of location quality.
- Payments, procurement ERP integration, predictive AI, route optimization, or public-facing dashboards.
- Multi-organization tenancy unless explicitly added with end-to-end authorization and isolation tests.

## 8. Success metrics
- 100% of approved deliveries link to a stock ledger movement and evidence/review trail, or a documented exception permitted by policy.
- No distributor can read or mutate another distributor's data in automated access-control tests.
- Zero duplicate ledger postings under repeated approve requests and idempotent retries.
- Admin can reconcile central + distributor + site balances against ledger totals.
- Admin can find a recorded delivery location on the map, see its site/distributor/quantity, and open the evidence review workspace within the application.
- Distributor can complete a valid site submission from a phone and can recover an offline draft after connectivity returns.
