# User Flows

This describes the flows in the current build. Deferred features are called out inline rather than implied.

## A. First deployment / admin bootstrap
1. Operator configures secrets and environment variables.
2. Operator runs a one-time CLI command to create the first admin account, supplying credentials securely through the terminal/environment prompt.
3. Operator optionally configures a public map style or raster providers through `VITE_MAP_STYLE_URL` / `VITE_MAP_TILE_URL` / `VITE_MAP_SATELLITE_TILE_URL` (empty uses OpenStreetMap streets + Esri satellite as a development/small-scale default). Admin signs in, rotates any temporary credential if supported, and configures organization display settings, units/bag weight and capture-time drift. Legacy geofence/accuracy settings are not part of the current UI.
4. Admin creates a campaign, creates/imports sites, invites distributors, records initial stock receipt, and allocates stock/targets.

## B. Admin allocates stock
1. Admin opens Inventory → Receive stock and enters a quantity in kg, source/reference and optional notes. The API accepts other units, but the current form posts kg only; there is no received-date field.
2. API converts to kg (when a unit is supplied) and writes a receipt movement into the central account in a DB transaction.
3. Admin opens Allocate to distributor, chooses a distributor and enters a quantity in kg.
4. API verifies central available balance and writes the transfer movement central → distributor. Assignments/targets are planned separately on the Campaigns screen. All changes are auditable.
5. UI refreshes ledger-derived balances and shows the movement reference.

## C. Distributor submits site distribution
1. Distributor signs in; dashboard shows assigned sites, allocated balance, available balance, target progress, pending submissions and draft queue.
2. Distributor opens an assigned site and confirms the correct location.
3. User grants location permission. UI shows coordinates/accuracy or a clear failure/retry path; no hidden/background location requests.
4. User captures a current photo (fallback upload only if policy permits, and label it as an alternate path), enters quantity and note, and reviews the captured/missing location context. No distance, geofence or location-quality warning is shown; submission and approval are allowed from any recorded place.
5. Client saves a local draft/idempotency key before upload if offline support is active.
6. Server validates scope, positive quantity, available stock net of pending reservations, geolocation ranges/quality, assigned site/campaign, file type/size and idempotency key; uploads private image and creates evidence + pending distribution record.
7. Client displays **Submitted — awaiting review** only after server acknowledgement. If offline, it shows **Saved on this device — not submitted**.

## D. Admin reviews delivery
1. Admin opens the Evidence review queue (optionally scoped by site or distributor) and inspects the image, site, distributor, quantity, time, captured/missing location, accuracy and non-location evidence-integrity flags.
2. Admin may approve (manual, from any recorded place), reject with reason, or accept an evidence-integrity/target exception with explicit reason and audit trail.
3. Approval service locks the relevant stock/account rows, verifies record is pending and reservation still valid, posts one distributor → site ledger movement, marks the distribution approved and creates audit event in one transaction.
4. Rejection records the reason, leaves ledger balance unchanged, and releases the pending reservation. The distributor sees the reason in My submissions; there is no in-app notification feed.
5. A repeated request is idempotent and must not post a second movement.

## E. Site/map investigation
1. Admin filters the map by campaign. The API also accepts a bounding box and distributor id; status/date filters are not exposed in the current map UI.
2. Map renders only distributor-recorded delivery points (submitted or approved; rejected/cancelled excluded) with a status legend and a synchronized list on OpenStreetMap streets by default, with a Map/Satellite switch for Esri imagery. Site reference coordinates and sites without deliveries are not plotted. Selecting a delivery shows its site, distributor, quantity and captured coordinates with OpenStreetMap/Google Maps and evidence-review links. Clustering is not implemented; a labelled coordinate board is used only if the map cannot initialize.
3. Site targets, progress and assignments remain in Campaigns/site analytics; the delivery map does not show site reference markers. Evidence flags are reviewed on the Evidence review screen, not in the map drawer.
4. Admin opens any image through an authorized short-lived URL and sees the relevant evidence metadata on the review screen.

## F. Offline distributor behavior
1. If offline before submission, the client saves an explicitly local draft, including quantity, notes and locally retained image/location according to documented browser storage limits.
2. UI reports pending local sync, not a successful server submission.
3. When connectivity returns, the queue resumes with the same idempotency key; upload progress/retry state is visible.
4. If the server accepted a previous attempt but the response was lost, retry returns the original record and does not create duplicates.
5. On logout, disclose that drafts may remain on the device and give a safe option to discard them; do not expose one user's draft to the next session.
