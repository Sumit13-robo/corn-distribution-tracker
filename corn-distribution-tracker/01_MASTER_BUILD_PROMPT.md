# MASTER PROMPT — Build a Production-Ready Corn Distribution Tracker

> **Implementation note (2026-10-23):** This is the original build brief. The repository was subsequently implemented with **Django 5.2 + Django REST Framework + PostgreSQL** instead of FastAPI/SQLAlchemy/Alembic, without PostGIS, and with native local development instead of Docker. The authoritative current stack and run instructions are in `docs/architecture/STACK_AND_REPO.md` and `README.md`. Product requirements that remain deferred are listed in `docs/product/PRD.md` and the README known limitations.

You are the lead product engineer, UX designer, backend engineer, frontend engineer, QA engineer, and release engineer. Build a real, maintainable web application for accountable corn stock allocation and field distribution. The output must be a working repository, not just mock screens or a written plan.

## Goal

Create a polished web app with two role-based sign-ins:

1. **Admin** — organization-wide control and visibility: live inventory position, distribution progress, map of assigned/delivered sites, distributor performance, submitted evidence photos, location context and non-location evidence-integrity flags, stock ledger, approvals, reports, and settings.
2. **Distributor** — a focused mobile-first workspace: own assigned sites, allocated stock/remaining stock, site targets, delivery history, and a guided flow to report a delivery/update with quantity, GPS, a fresh camera image, notes, and submission status.

The core promise is traceability: for each site, the system must show its target/allocation, actual submitted quantity, verified/approved quantity, remaining planned quantity, distributor, status, location, and evidence trail. Every stock change must be explainable in an append-only ledger.

## Read before coding

Read the entire project pack, especially:

- `AGENTS.md`
- `product/PRD.md`
- `product/USER_FLOWS.md`
- `product/ACCEPTANCE_CRITERIA.md`
- `architecture/STACK_AND_REPO.md`
- `architecture/DOMAIN_MODEL.md`
- `architecture/INVENTORY_LEDGER.md`
- `architecture/API_CONTRACT.md`
- `architecture/SECURITY_AND_PRIVACY.md`
- `architecture/GEO_PHOTO_EVIDENCE.md`
- `architecture/OFFLINE_SYNC.md`
- `design/UX_SPEC.md`, `design/SCREEN_SPECS.md`, and `design/DESIGN_SYSTEM.md`
- `handoffs/file_map.md` and all per-file handoffs for the files you implement

Do not silently contradict those contracts. Where two instructions conflict, security, ledger integrity, and explicit acceptance criteria take precedence; document any unavoidable trade-off.

## Required stack and repository

Use the monorepo and stack documented in `architecture/STACK_AND_REPO.md`: React + TypeScript + Vite for the web client; Django 5.2 + Django REST Framework for the API; PostgreSQL with Django ORM migrations (no PostGIS requirement); private S3-compatible object storage for photos; native PostgreSQL + Django + Vite for local development. Use stable, mutually compatible versions available at implementation time, commit lockfiles, and do not install deprecated packages just to match a sample.

Use a configurable production map-tile provider. Do not depend on a public/free tile endpoint without reviewing that provider's usage policy and production suitability. Keep secrets server-side. Use a generated API client/types from the API contract where practical, but do not let code generation obscure validation or permissions.

## Non-negotiable behavior

### Roles and authorization
- Every server endpoint that reads or mutates data must enforce authentication and role/ownership scope on the server. Hiding a button in the UI is not authorization.
- Admins may view/manage organization data according to the permission matrix.
- Distributors may access only their own profile, assigned sites/campaigns, own submissions/evidence, and the stock available to their stock account. They must never query another distributor by changing an ID.
- Create initial admin using a one-time CLI/bootstrap command or secure deployment procedure. Do not expose a public “make me admin” endpoint or hardcode credentials.
- Add password hashing, rate limiting, safe error messages, secure session/refresh behavior, password reset/invitation expiry, and audit events for sensitive actions.

### Stock, distribution and financial-like integrity
- Persist canonical quantities in kg using decimal/numeric database types; do not use binary floating-point for inventory arithmetic.
- All changes to stock must be represented in immutable stock ledger movements. Do not maintain a separately editable `current_quantity` as the source of truth.
- A distributor delivery submission is pending review. Pending records reserve stock, so a user cannot submit more than the available balance by submitting multiple requests in parallel.
- Approve/reject/post operations must use database transactions and concurrency protection. Approval posts exactly one movement, is idempotent, and has an auditable actor/time/reason. Rejected submissions release their reservation; corrections to posted records use a compensating movement, never destructive edits.
- Prevent negative balances unless an explicit, tested admin exception policy is implemented. Check target/assignment overages and require an explicit admin override with reason if supported.
- Define dashboard formulas in `architecture/INVENTORY_LEDGER.md`; keep pending, approved/verified, assigned, and remaining quantities separate in all UI and reports.

### Geotagged photo evidence
- Request geolocation only when the distributor starts a check-in/submission flow; explain why it is needed.
- Capture a fresh camera image where the device/browser allows it, using a mobile-friendly camera flow. If browser/device support prevents camera capture, clearly label the alternate upload path and apply the policy documented in `architecture/GEO_PHOTO_EVIDENCE.md`.
- Persist latitude/longitude, reported accuracy in metres, client capture time, device-reported location time if available, server receipt time, submitting user, optional site reference coordinates, informational distance when both points exist, evidence status/flags, cryptographic image hash, storage key, and metadata validation results.
- Validate coordinate ranges and reject impossible values. Do not flag or block on location quality, missing location, geofence distance or EXIF GPS difference. Generate only non-location evidence-integrity flags such as capture/upload time mismatch, duplicate content hash or unexpected file type.
- Do not falsely claim that browser geolocation or EXIF can prove the image is unmanipulated. Display evidence confidence and integrity flags, and let the admin decide. Any approval from any recorded place is manual and audited; an exception reason is required only for non-location evidence integrity or an exceeded assignment target.
- Store originals privately, serve photos only through short-lived signed URLs after authorization, keep auditable evidence records, and avoid logging sensitive image contents or raw credentials.

### Maps, analytics and usability
- Show site points and status filters on the admin map; clusters should remain usable for many sites. Selecting a point opens its site, assignment, quantity summary, distributor, latest evidence, and history.
- Dashboard metrics must distinguish allocated, distributor-held, submitted/pending, approved/distributed, remaining, and variance; never count pending deliveries as approved delivery.
- Every screen must include meaningful loading, empty, error, permission-denied, and retry states. No fake metrics or fake map pins in production mode.
- Admin web UI should look professional and operational rather than a generic template. Distributor UI must work well on a narrow mobile viewport, with large touch targets, clear progress, low-bandwidth support, and confirmation before submission.
- Meet WCAG 2.2 AA intent: semantic HTML, visible focus, accessible labels, keyboard use, adequate contrast, non-color-only statuses, reduced-motion support, and useful screen-reader text.

### Offline and duplicate protection
- Let distributors save drafts during poor connectivity; show whether a draft is local, queued, uploading, submitted, rejected, or approved.
- Queue operations with stable client-generated idempotency keys. Server retries must not double-create evidence records or post stock movements.
- Do not show “submitted” until the server confirms the request. An offline draft is not an official distribution record.
- If offline evidence upload is supported, encrypt or minimize locally retained data where feasible, constrain access to the signed-in user, handle logout safely, and document storage limitations. Never silently drop queued records.

## Recommended implementation sequence

1. Inspect the existing workspace/repository before modifying anything. Preserve working code and user files.
2. Create the repository skeleton, environment templates, health endpoint, Django settings, models, and first Django migration.
3. Implement domain services and server authorization before frontend data screens.
4. Implement auth, invitations/bootstrap, campaigns/sites/assignments, stock ledger, distributor submission, evidence storage/geo validation, approval/rejection, audit log, and analytics endpoints.
5. Add focused backend tests for authorization isolation, stock race conditions, duplicate idempotency, approval/rejection, geo-validation flags, and analytics formulas.
6. Build the frontend API/session layer and route guards; implement Admin pages and Distributor mobile workflow against real endpoints.
7. Add integration/component tests, offline draft behavior, accessible UI states, and responsive visual QA.
8. Add observability, production configuration, migration/backup/restore notes, security checklist, and deployment runbook.
9. Run formatters, type checks, lints, migration checks, backend tests, frontend tests, production builds, dependency audit where available, and smoke tests. Fix failures rather than documenting them away.
10. Update all handoff statuses and final README with exact commands, implemented features, limitations, environment variables, and release steps.

## File-level handoff discipline

`handoffs/file_map.md` is the source of truth for planned files. Before changing a file, read its matching note in `handoffs/per-file/`. Implement the file's stated responsibility and acceptance criteria. Add tests alongside behavior. If a planned file is unnecessary, update the map and handoff note with a reason—do not silently omit it. If you add files, add them to the map and write a handoff note for each.

Use these ownership boundaries when parallelizing:
- Backend/data agent: `apps/api/**`, migrations, API contract alignment.
- Frontend agent: `apps/web/**`, UI/design spec alignment, typed API integration.
- QA agent: `apps/api/tests/**`, frontend tests, acceptance suite, bug reproduction.
- DevOps/release agent: environment template, reverse proxy/deployment runbook, CI, monitoring and backup instructions.
- Lead integrator: shared contracts, merge resolution, run full test suite, verify RBAC and ledger behavior end-to-end.

Agents must not independently invent endpoint shapes, quantity formulas, enum values, or role semantics. The contracts in the architecture docs are canonical.

## Completion bar

Do not claim the app is production-ready until:
- a clean checkout can be installed and started using the README;
- database migrations create a complete schema;
- admin bootstrap works without hardcoded credentials;
- a distributor cannot access a different distributor's records by changing route/API IDs;
- concurrent submissions cannot overspend the same stock balance;
- approval posts one ledger movement; retrying does not duplicate it; rejection releases reservation;
- private image URLs require authorized issuance and expire;
- GPS coordinates/accuracy/time, optional site-distance context, hash and non-location evidence-integrity flags are saved; location never blocks approval;
- map, dashboard, site pages, photo review, and distributor delivery submission use the real API;
- critical tests pass and build/lint/type check results are reported honestly;
- production env, HTTPS, CORS, backup/restore, monitoring, and incident/release procedures are documented.

Start by outputting a concise repository assessment and phased plan, then implement the repository directly. Do not stop at a plan, do not replace the requested build with a mockup, and do not invent external integrations or credentials.
