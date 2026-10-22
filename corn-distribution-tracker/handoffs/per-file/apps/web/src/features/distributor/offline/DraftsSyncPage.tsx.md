# File Handoff: `apps/web/src/features/distributor/offline/DraftsSyncPage.tsx`

**Status:** IMPLEMENTED
**Primary owner:** Frontend
**File purpose:** Distributor drafts and sync queue screen.

## Current implementation

Shows online/offline state, photo counts, draft states and failed-sync messages; supports continuing a draft, per-draft retry, sync-all, and confirmed discard/removal. Draft state is read from the user-scoped local queue and updates live. It never claims a draft is submitted until a server record id exists.

## Verification

Covered by web unit tests, the Playwright offline-draft workflow (8 passed), and the 360 px screenshot audit.

## Unresolved issues

None known. Photos fall back to memory when IndexedDB is unavailable.
