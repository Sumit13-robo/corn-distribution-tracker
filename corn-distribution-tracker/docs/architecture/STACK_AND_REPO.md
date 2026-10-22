# Stack and Repository Contract

## Stack
- **Web:** React, TypeScript strict mode, Vite, React Router, TanStack Query (or equivalent server-state cache), React Hook Form + Zod (or equivalent schema-driven forms), accessible component primitives, and MapLibre GL JS (or Leaflet if justified and documented).
- **API:** Python supported stable release at implementation time, FastAPI, Pydantic v2-compatible schemas, SQLAlchemy 2, Alembic, PostgreSQL + PostGIS, structured logging, server-side rate limiting.
- **Evidence storage:** S3-compatible private bucket with short-lived signed URLs, upload size/type controls and optional thumbnail derivatives.
- **Local dev/deploy:** Docker Compose for web/API/PostgreSQL/PostGIS; external object storage in production. Do not embed cloud keys in the frontend.
- **Tests:** Pytest, API/client integration tests, frontend component tests (Vitest + Testing Library or equivalent), and Playwright browser E2E for the critical submission/review/offline flow.

Pin compatible dependencies in lockfiles. Choose stable versions during implementation and verify library APIs against official docs rather than relying on deprecated examples.

## Target repository

```text
.
├── AGENTS.md
├── README.md
├── .env.example
├── docker-compose.yml
├── Makefile
├── docs/                         # optional mirrored product/architecture docs
├── apps/
│   ├── api/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── alembic.ini
│   │   ├── alembic/
│   │   │   ├── env.py
│   │   │   └── versions/0001_initial_schema.py
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── core/{config.py,security.py}
│   │   │   ├── db/{session.py,base.py}
│   │   │   ├── models/*.py
│   │   │   ├── schemas/*.py
│   │   │   ├── api/{dependencies.py,router.py,routes/*.py}
│   │   │   └── services/*.py
│   │   └── tests/*.py
│   └── web/
│       ├── Dockerfile
│       ├── package.json
│       ├── vite.config.ts
│       └── src/...
├── infra/                        # optional reverse proxy / deployment manifests
└── handoffs/                     # retain/update these specs in repo
```

## Architecture boundaries
- Frontend never connects directly to PostgreSQL or object storage.
- Route handlers validate input and call domain services; ledger/evidence rules live in services, not in React and not only in route code.
- Database schema is changed via Alembic migrations.
- API response and enum values are canonical in `API_CONTRACT.md` and Python schemas; frontend types mirror them and are checked for drift.
- Server-side filtering, pagination, and scoping are mandatory. Do not fetch the entire organization then filter in the browser.
- Use PostGIS geometry/ geography or validated numeric coordinates for map data and indexed distance checks. State SRID/unit assumptions explicitly.
- A thumbnail is a convenience; originals remain private. Storage keys must be opaque and must not embed names, addresses, or other personal information.
