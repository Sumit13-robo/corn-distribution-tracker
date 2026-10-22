# Product Requirements Document

## 1. Problem
Corn quantity is distributed across locations by distributors. The organization needs a common record of available stock, allocations, site-level delivery progress, and photo/location evidence so that supervisors can reconcile physical deliveries and assign accountability.

## 2. Product outcomes
- Know how much corn was received, allocated to each distributor, submitted as delivered, approved as delivered, and remains in stock.
- See all sites on a map, with status and quantities, and inspect a site’s delivery history.
- Make distributor updates accountable through user identity, time, geolocation evidence, photo hash, site distance, and admin review.
- Identify over/under delivery, pending approvals, missing evidence, suspicious geo-data, low photo coverage, and distributor performance.
- Work reliably on mobile devices in areas with weak connectivity.

## 3. Roles
### Admin
May manage distributor accounts/invitations, campaigns, sites, assignments/targets, inventory receipts and allocations, evidence review, approvals/rejections, adjustments with reasons, analytics, exports, and organization settings. Every sensitive change creates an audit event.

### Distributor
May view own profile, assigned campaigns/sites, own allocated/available stock, site targets, own submissions and review feedback, and create a delivery submission at an assigned site. Cannot create administrators, alter stock directly, approve own submissions, see another distributor's private evidence, or change an approved ledger entry.

## 4. Core entities
- Campaign: a named distribution effort with dates, status, and unit/display preferences.
- Site: named physical delivery point with address/description, expected latitude/longitude, geofence configuration, and active state.
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
- Admin can create/edit/deactivate a site and set coordinates, expected location radius and quantity target/assignment.
- Site markers convey status using both color and text/icon. Marker selection shows target, submitted, approved, pending and remaining planned amount, distributor, last visit and evidence status.
- A site can have multiple visits; do not overwrite historic visits with the latest update.

### Distributor workflow
- List assignments with target, completed/approved quantity, quantity pending review, remaining target, available stock and due/status information.
- Open a site, check location permission and display GPS accuracy; provide clear retry guidance if location is unavailable or too inaccurate.
- Capture a fresh photo, enter quantity (unit is explicit), optional note, and submit. Show distance to expected site and any warning before final submission.
- Save a draft when offline, queue retry safely, and distinguish local draft from server-confirmed submission.
- A distributor can see rejection reason and submit a new/corrected report without rewriting previous evidence or a posted ledger movement.

### Admin evidence review
- View all authorized evidence with original timestamp, server timestamp, submitting user, site, coordinates, reported accuracy, expected coordinates, calculated distance, image hash, duplicate warning, EXIF cross-check when available, and validation flags.
- Approve or reject with optional/required review reason according to the action; approval posts a stock movement atomically. Rejection must not change stock and releases the reserved quantity.
- Admin override of a geo warning requires a reason and is auditable.
- Photos load from short-lived signed URLs; no public bucket or permanent public image URL.

### Analytics and exports
- Overview totals: physical stock by account; total received; currently held by distributors; submitted/pending quantity; approved/distributed quantity; remaining assigned target; rejected quantity; open review count; evidence completeness; flagged submissions.
- Filters: campaign, date range, distributor, site, status and region/location where supported.
- Distributor performance: assigned target, submitted, approved, pending, rejected, stock remaining, on-time visits where due dates exist, evidence quality and exception rate. Make denominators explicit.
- Site performance: target, submitted, approved, pending, remaining target, last visit and evidence coverage.
- CSV exports require permission, filters must match the visible result, large exports should be bounded or generated asynchronously later, and exports must not leak hidden records.

## 6. Non-functional requirements
- Security: secure auth/session management, rate limiting, password hashing, server RBAC, secure headers, strict CORS, private image storage, secret management, safe errors and audit trail.
- Reliability: transactional ledger operations, idempotent mutation endpoints, migrations, backup and tested restore instructions.
- Performance: paginated lists, indexed filters, clustered map points, bounded API responses, thumbnail derivatives and signed URLs.
- Accessibility: WCAG 2.2 AA intent.
- Mobile: distributor workflow optimized for modern Android/iOS browsers; camera and geolocation permission states handled gracefully.
- Privacy: collect location only during a relevant site update, state why it is collected, protect evidence, and define retention configurable by policy.
- Observability: structured logs without sensitive payloads, request IDs, health/readiness checks, exception monitoring and operational alerts for repeated failures.

## 7. Out of scope for first release
- Native mobile app; use responsive web/PWA.
- Automated face recognition, identity recognition, or covert tracking.
- Claims that GPS, EXIF, or image hashes prove a physical delivery occurred.
- Payments, procurement ERP integration, predictive AI, route optimization, or public-facing dashboards.
- Multi-organization tenancy unless explicitly added with end-to-end authorization and isolation tests.

## 8. Success metrics
- 100% of approved deliveries link to a stock ledger movement and evidence/review trail, or a documented exception permitted by policy.
- No distributor can read or mutate another distributor's data in automated access-control tests.
- Zero duplicate ledger postings under repeated approve requests and idempotent retries.
- Admin can reconcile central + distributor + site balances against ledger totals.
- Admin can find a site on the map and inspect its latest evidence without leaving the application.
- Distributor can complete a valid site submission from a phone and can recover an offline draft after connectivity returns.
