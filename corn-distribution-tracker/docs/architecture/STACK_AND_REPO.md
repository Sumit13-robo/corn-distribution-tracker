# Stack and Repository Contract

## Stack
- **Web:** React 19, TypeScript strict mode, Vite, React Router, TanStack Query, accessible primitives, and MapLibre GL JS with OpenStreetMap streets + Esri World Imagery satellite by default (or a public style/tile URL configured through `VITE_MAP_STYLE_URL` / `VITE_MAP_TILE_URL` / `VITE_MAP_SATELLITE_TILE_URL`).
- **API:** Python 3.12+ (validated on 3.14), Django 5.2, Django REST Framework, PostgreSQL, Django's ORM and session framework, structured request logging, and server-side rate limiting.
- **Evidence storage:** private local directory in development, or an S3-compatible bucket in production. Evidence is served only through short-lived signed URLs after server authorization.
- **Local development:** a local PostgreSQL instance plus two native dev servers (`manage.py runserver` and `vite`). There is no PostGIS dependency; coordinates are validated `NUMERIC` fields. Production can run Django under Gunicorn behind a TLS reverse proxy that serves the built SPA and proxies `/api/`.
- **Tests:** pytest + pytest-django against real PostgreSQL, Vitest + Testing Library for frontend units, and Playwright browser E2E for the submission/review/offline loop.

Pin compatible dependencies in lockfiles. Choose stable versions during implementation and verify library APIs against official docs rather than relying on deprecated examples.

## Target repository

```text
.
├── AGENTS.md
├── README.md
├── .env.example
├── Makefile
├── docs/                         # product, architecture, design and ops contracts
├── apps/
│   ├── api/
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
│       ├── nginx.conf            # optional production reverse-proxy sample
│       ├── package.json
│       ├── vite.config.ts
│       ├── e2e/                  # Playwright setup and workflow specs
│       └── src/...
└── handoffs/                     # file ownership map and per-file notes
```

## Architecture boundaries
- Frontend never connects directly to PostgreSQL or object storage.
- URL handlers validate input and call domain services; ledger/evidence rules live in services, not in React and not only in view code.
- Database schema is changed via Django migrations. Production never relies on automatic schema creation.
- API response and enum values are canonical in `API_CONTRACT.md`; DRF serializers enforce the input boundary and frontend types mirror the responses.
- Server-side filtering, pagination, and scoping are mandatory. Do not fetch the entire organization then filter in the browser. The API implements this; several current admin tables intentionally request a bounded first page (for example, 25 or 100 rows) and sort only that loaded page, without exposing pagination controls.
- Coordinates are validated decimals; optional geodesic distance is calculated in the domain service for context only. Location quality and geofence distance never gate approval. There is no PostGIS geometry column in this build, so indexed distance search at very large scale would be a future migration.
- A thumbnail is a convenience; originals remain private. Storage keys are opaque and do not embed names, addresses, or other personal information.
- Only public configuration may use the `VITE_` prefix. Server secrets must never appear in a Vite variable, the browser bundle, logs, or screenshots.
