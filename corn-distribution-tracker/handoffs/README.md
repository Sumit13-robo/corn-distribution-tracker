# Handoff Workflow

## Recommended phases
1. **Lead/spec alignment:** confirm existing repo and preserve it; reconcile `API_CONTRACT.md` to schemas before parallel work.
2. **Platform:** environment config, Docker, DB session/base, health checks, model layer and Alembic migration.
3. **Backend security and domain:** auth/roles, campaigns/sites/assignments, inventory ledger, deliveries/evidence, analytics/audit.
4. **Backend QA:** test isolation, non-negative stock, concurrent submissions, idempotent approvals, invalid geo/photo metadata and formula definitions.
5. **Frontend foundation:** routes/providers, API client, session/permissions, design tokens and shared components.
6. **Admin workflows:** overview, map, site/distributor/assignment/inventory management, evidence review, analytics.
7. **Distributor workflows:** assigned sites, location/photo capture, submission, status/history, offline draft queue.
8. **Integration and release:** run acceptance criteria, check responsive/accessibility, Docker smoke test, migration, security and release docs.

## How to hand off between agents
Every handoff should state: files owned; source-of-truth docs read; exports/endpoints produced; contracts consumed; tests added/run; known limitations; commands/branch/commit; and open questions. The lead integrator resolves shared API/type changes rather than letting agents fork contracts.

## Status protocol
In `file_map.md`, mark each file `PLANNED`, `IN_PROGRESS`, `IMPLEMENTED`, `TESTED`, or `DEFERRED`. Do not mark `TESTED` without actual test evidence. This handoff pack starts with all source files `PLANNED`.
