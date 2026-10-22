# Stack and Repository Contract

## Stack
- **Web:** React 19, TypeScript strict mode, Vite, React Router, TanStack Query, accessible primitives, and MapLibre GL JS when `VITE_MAP_STYLE_URL` is configured.
- **API:** Python 3.12+ (validated on 3.14), Django 5.2, Django REST Framework, PostgreSQL, Django's ORM and session framework, structured request logging, and server-side rate limiting.
- **Evidence storage:** private local directory in development, or an S3-compatible bucket in production. Evidence is served only through short-lived signed URLs after server authorization.
- **Local dev/deploy:** Docker Compose for web/API/PostgreSQL, or a local PostgreSQL instance plus two dev servers. There is no PostGIS dependency; coordinates are validated `NUMERIC` fields.
- **Tests:** pytest + pytest-django against real PostgreSQL, Vitest + Testing Library for frontend units, and Playwright browser E2E for the submission/review/offline loop.

Pin compatible dependencies in lockfiles. Choose stable versions during implementation and verify library APIs against official docs rather than relying on deprecated examples.

## Target repository

```text
.
├── AGENTS.md
├── README.md
├── .env.example
├── docker-compose.yml
├── Makefile
├── docs/                         # product, architecture, design and ops contracts
├── apps/
│   ├── api/
│   │   ├── Dockerfile
│   │   ├── manage.py
│   │   ├── pyproject.toml
│   │   ├── pytest.ini
│   │   ├── requirements.txt
│   │   ├── config/               # Django settings, URLs, WSGI/ASGI
│   │   ├── corn/
│   │   │   ├── migrations/       # schema + append-only database triggers
│   │   │   ├── management/       # create_admin, issue_password_reset
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views/            # thin DRF endpoint handlers
│   │   │   └── services/         # ledger, evidence, auth, analytics, audit
│   │   └── tests/*.py
│   └── web/
│       ├── Dockerfile
│       ├── nginx.conf
│       ├── package.json
│       ├── vite.config.ts
│       ├── e2e/                  # Playwright setup and workflow specs
│       └── src/...
├── infra/                        # optional reverse proxy / deployment manifests
└── handoffs/                     # file ownership map and per-file notes
```

## Architecture boundaries
- Frontend never connects directly to PostgreSQL or object storage.
- URL handlers validate input and call domain services; ledger/evidence rules live in services, not in React and not only in view code.
- Database schema is changed via Django migrations. Production never relies on automatic schema creation.
- API response and enum values are canonical in `API_CONTRACT.md`; DRF serializers enforce the input boundary and frontend types mirror the responses.
- Server-side filtering, pagination, and scoping are mandatory. Do not fetch the entire organization then filter in the browser.
- Coordinates are validated decimals; distance and geofence checks run in the domain service. There is no PostGIS geometry column in this build, so indexed distance search at very large scale would be a future migration.
- A thumbnail is a convenience; originals remain private. Storage keys are opaque and do not embed names, addresses, or other personal information.
- Only public configuration may use the `VITE_` prefix. Server secrets must never appear in a Vite variable, the browser bundle, logs, or screenshots.
