# User Flows

## A. First deployment / admin bootstrap
1. Operator configures secrets and environment variables.
2. Operator runs a one-time CLI command to create the first admin account, supplying credentials securely through the terminal/environment prompt.
3. Admin signs in, rotates any temporary credential if supported, configures organization display settings, units/bag weight, geofence radius and map provider.
4. Admin creates a campaign, creates/imports sites, invites distributors, records initial stock receipt, and allocates stock/targets.

## B. Admin allocates stock
1. Admin opens Inventory → Receive Stock and enters source/reference, quantity/unit, and date.
2. API converts to kg and writes a receipt movement into the central account in a DB transaction.
3. Admin opens Allocations, chooses campaign/distributor, enters quantity and optional assignment targets.
4. API verifies central available balance, writes transfer movement central → distributor, and writes/updates assignment rows. All changes are auditable.
5. UI refreshes ledger-derived balances and shows receipt/allocation reference.

## C. Distributor submits site distribution
1. Distributor signs in; dashboard shows assigned sites, allocated balance, available balance, target progress, pending submissions and draft queue.
2. Distributor opens an assigned site and confirms the correct location.
3. User grants location permission. UI shows coordinates/accuracy or a clear failure/retry path; no hidden/background location requests.
4. User captures a current photo (fallback upload only if policy permits, and label it as an alternate path), enters quantity and note, and reviews the site distance/quality warnings.
5. Client saves a local draft/idempotency key before upload if offline support is active.
6. Server validates scope, positive quantity, available stock net of pending reservations, geolocation ranges/quality, assigned site/campaign, file type/size and idempotency key; uploads private image and creates evidence + pending distribution record.
7. Client displays **Submitted — awaiting review** only after server acknowledgement. If offline, it shows **Saved on this device — not submitted**.

## D. Admin reviews delivery
1. Admin opens Review Queue or a site pin and inspects the image, site, distributor, quantity, time, GPS accuracy, distance and warning flags.
2. Admin may approve, reject with reason, or accept a flagged location exception with explicit reason and audit trail.
3. Approval service locks the relevant stock/account rows, verifies record is pending and reservation still valid, posts one distributor → site ledger movement, marks the distribution approved and creates audit event in one transaction.
4. Rejection records the reason, leaves ledger balance unchanged, releases the pending reservation, and notifies the distributor in-app.
5. A repeated request is idempotent and must not post a second movement.

## E. Site/map investigation
1. Admin filters by campaign, date and status.
2. Map renders current sites with clusters/status legend; list/table and map filters stay synchronized.
3. Selecting a site shows target, approved quantity, pending quantity, remaining target, recent submissions, evidence flags and event history.
4. Admin opens any image through an authorized short-lived URL and sees the relevant evidence metadata.

## F. Offline distributor behavior
1. If offline before submission, the client saves an explicitly local draft, including quantity, notes and locally retained image/location according to documented browser storage limits.
2. UI reports pending local sync, not a successful server submission.
3. When connectivity returns, the queue resumes with the same idempotency key; upload progress/retry state is visible.
4. If the server accepted a previous attempt but the response was lost, retry returns the original record and does not create duplicates.
5. On logout, disclose that drafts may remain on the device and give a safe option to discard them; do not expose one user's draft to the next session.
