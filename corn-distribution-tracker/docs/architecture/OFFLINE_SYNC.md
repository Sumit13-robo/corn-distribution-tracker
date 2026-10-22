# Offline Draft and Sync Contract

## Scope
The distributor flow should handle intermittent field connectivity without falsely claiming an upload succeeded. The first release must at minimum support local draft text/quantity and explicit queued state; photo retention and queued media upload must follow secure browser storage constraints documented in implementation notes.

## Client states
`LOCAL_DRAFT` → `QUEUED` → `UPLOADING` → `SUBMITTED`; terminal server states `APPROVED` or `REJECTED`. An upload failure returns to `QUEUED` with retry details. `LOCAL_DRAFT`/`QUEUED` are not official distribution records.

## Requirements
- Generate and persist an idempotency key when a draft is created; reuse it across retries and reloads.
- Server persists a unique idempotency scope and returns the existing result on duplicate request. Do not create multiple records/evidence objects or stock movements on retries.
- Display last sync time, queue count, upload progress/errors, and a manual retry action. Do not spin forever without user feedback.
- Keep queue operations ordered where dependencies exist; each failed item must be inspectable/retryable or discardable with confirmation.
- Scope local records to the currently signed-in user. On logout, either ask whether to discard unsynced drafts or encrypt/retain them in a design that prevents the next user from reading them. Clearly disclose what remains on-device.
- Do not trust client timestamps or client-calculated balances; server revalidates stock, assignment, site, and state when synced.
- If stock became insufficient while offline, keep the draft and explain the conflict; do not silently change quantity or mark success.
- Use a service worker only where it provides reliable benefit and has clear cache rules. Never cache authenticated API responses, private signed image URLs, or admin data in a public/shared cache.

## Test cases
Offline draft saved and restored; network resumes; repeated retry after lost response; expired session during sync; user changes account; duplicate image; API says insufficient stock; upload succeeds but final record request fails; app reload during queue; discard confirmation; no false submitted status.
