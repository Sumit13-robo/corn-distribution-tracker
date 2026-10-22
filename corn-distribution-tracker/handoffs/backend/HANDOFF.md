# Backend Agent Handoff

## Own
`apps/api/**`, Alembic migrations, API implementation and backend tests. Coordinate endpoint/schema changes with the lead before changing contracts.

## Sequence
1. Config + DB session + health endpoint.
2. Models and initial migration; verify PostGIS extension/index approach on a clean database.
3. Auth/session/RBAC and controlled admin bootstrap CLI (add a file handoff if a new CLI module is created).
4. Campaigns/sites/assignments and account setup.
5. Inventory ledger and concurrency protection.
6. Evidence storage + geo validation + submission/approval/rejection.
7. Analytics/export/audit, tests and OpenAPI review.

## Hard gates
- Do not add a “current stock” mutable field as truth.
- Submit reservation and approval operations must be race-safe.
- Approval must atomically post one movement and audit event.
- All data queries are scoped by role/ownership on the server.
- A distributor never chooses the `reviewed_by` user; derive it from auth.
- Private storage and signed URLs only.
- Do not return EXIF/coordinates for records the caller cannot access.

## Report
List migration command/results, API route list, tests run, concurrency strategy, how admin bootstrap works, and any external services needed.
