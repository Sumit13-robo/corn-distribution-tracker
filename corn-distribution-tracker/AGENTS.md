# Repository-wide Agent Rules

## Required behavior
- Read `01_MASTER_BUILD_PROMPT.md` and relevant architecture/design docs before implementation.
- `handoffs/file_map.md` and `handoffs/per-file/` define the ownership and acceptance contract for each planned file.
- Inspect existing files and preserve valid work. Do not overwrite unrelated project content.
- Build the smallest complete, coherent system; no dead buttons, fake APIs, hardcoded passwords, production demo data, or TODO-only implementations for required features.
- Prefer typed contracts, small modules, dependency injection, predictable error handling, and explicit state transitions.
- Add or update a handoff note whenever a new file is added or a file's responsibility changes.

## Security and data integrity
- Server authorization is authoritative. Apply role and record-ownership scope in every route/service.
- Never ship secrets in source code, Vite variables, logs, screenshots, errors, or commits. Only public configuration may use a `VITE_` prefix.
- Validate all external input at the API boundary. Use parameterized ORM/database access. Avoid leaking whether another user's account exists.
- Use decimals for quantities, database transactions for ledger transitions, row locks or equivalent concurrency control, unique idempotency keys, and immutable audit/ledger records.
- Evidence images remain private. Signed URLs are short-lived and generated only after authorization.
- Do not describe GPS/EXIF signals as proof against sophisticated spoofing. Record flags and uncertainty honestly.
- Never put real personal data or real geotagged images in fixtures, logs, or committed example files.

## Frontend standards
- TypeScript strict mode. Avoid `any`; justify every unavoidable use.
- Use shared API/error/session code instead of hand-rolled fetch logic in each screen.
- Include loading, empty, error, retry, permission denied, and responsive states.
- UI permissions are supplementary; endpoint permissions are mandatory.
- Meet accessibility and mobile requirements in `design/UX_SPEC.md`.

## Backend standards
- Follow FastAPI router -> schema validation -> service/domain logic -> data model layers.
- Keep route handlers thin. Keep stock rules and evidence validation in services with unit/integration tests.
- Use Alembic migrations; never rely on automatic `create_all` in production.
- Keep API response shapes aligned to `architecture/API_CONTRACT.md`.
- Expose readiness/liveness health checks without exposing secrets or internal stack traces.

## Workflow and evidence
- Run formatting, linting, type checks, relevant tests, migration checks, and production builds after changes.
- Report command results truthfully. Do not say tests pass if not run or if failed.
- Update status in the handoff notes and add a concise implementation summary with files changed, tests run, unresolved issues, and exact run commands.
