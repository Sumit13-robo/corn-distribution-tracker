# Frontend Agent Handoff

## Own
`apps/web/**`. Use `API_CONTRACT.md` as the source of truth; if backend contract lacks a response field, raise it with lead/backend rather than hardcoding fake data.

## Sequence
1. Session/API/query foundation and router guards.
2. Design tokens and shared layout/form/table/status/error components.
3. Login and Admin shell/navigation.
4. Admin overview, map, sites, distributors, inventory, evidence review, analytics/settings.
5. Distributor mobile dashboard, assigned sites, detail, delivery/photo/GPS workflow, history and offline drafts.
6. Accessibility/responsive QA and component/E2E tests.

## Hard gates
- No mock KPI values in production routes.
- Do not report server submission success until server acknowledgement.
- Do not store long-lived bearer/refresh secrets in localStorage.
- Clear private query cache on logout/account switch.
- Any file/photo preview must use authorized API or upload state; never a guessed public bucket URL.
- Location permission prompt starts only after user action and clearly explains purpose.
- Show pending vs approved as different states/quantities.

## Report
List pages completed, endpoints consumed, keyboard/mobile checks, tests/build results, and missing API contract fields.

## Final verification (2026-10-22)
All planned screens and the offline delivery flow are implemented. 14 Vitest tests and 8 Playwright E2E tests pass; the browser flow covers session restore, photo/geolocation submission, evidence review/approval, approved history, offline QUEUED→SUBMITTED sync and a 360 px viewport check. Browser E2E also exposed and drove fixes for the assignment nested-site response, immediate location persistence and mobile header/navigation overflow.
