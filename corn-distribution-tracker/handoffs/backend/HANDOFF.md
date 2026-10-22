# Backend Agent Handoff

## Own
`apps/api/**`: Django/DRF configuration, models/migrations, serializers, views, services, management commands and backend tests. Coordinate endpoint/schema changes with the lead before changing contracts.

## Sequence
1. Settings + PostgreSQL ORM + health endpoints.
2. Models and Django migrations; verify append-only triggers on a clean database.
3. Session/CSRF auth, RBAC and controlled admin bootstrap command.
4. Campaigns/sites/assignments and account setup.
5. Inventory ledger and concurrency protection.
6. Evidence storage + geo validation + submission/approval/rejection.
7. Analytics/export/audit, tests and API contract review.

## Hard gates
- Do not add a “current stock” mutable field as truth.
- Submit reservation and approval operations must be race-safe.
- Approval must atomically post one movement and audit event.
- All data queries are scoped by role/ownership on the server.
- A distributor never chooses the `reviewed_by` user; derive it from the session.
- Private storage and short-lived signed URLs only.
- Do not return EXIF/coordinates for records the caller cannot access.
- Never log raw invitation/reset tokens or session/CSRF secrets.

## Report
List migration commands/results, route list, tests run, concurrency strategy, how admin bootstrap works, and any external services needed.
