# File Map and Ownership

Status values: `PLANNED`, `IN_PROGRESS`, `IMPLEMENTED`, `TESTED`, `DEFERRED`, `REMOVED`. Each target file has a corresponding handoff note under `handoffs/per-file/`, with its target path repeated in the note. Removed files keep their note for history.

## Backend API

| Target file | Owner | Responsibility | Handoff note | Status |
|---|---|---|---|---|
| `apps/api/.dockerignore` | Backend | Container build-context exclusions, including local secrets and evidence; used by Railway's Docker build | [`per-file/apps/api/.dockerignore.md`](per-file/apps/api/.dockerignore.md) | IMPLEMENTED |
| `apps/api/.env.railway.example` | DevOps | Safe Railway variable template for Postgres, bucket, proxy, cookies and runtime | [`per-file/apps/api/.env.railway.example.md`](per-file/apps/api/.env.railway.example.md) | IMPLEMENTED |
| `apps/api/Dockerfile` | Backend | Non-root API image; copies start/release scripts and honors Railway's `PORT` | [`per-file/apps/api/Dockerfile.md`](per-file/apps/api/Dockerfile.md) | IMPLEMENTED |
| `apps/api/bin/release.sh` | Backend / DevOps | Railway pre-deploy migration command | [`per-file/apps/api/bin/release.sh.md`](per-file/apps/api/bin/release.sh.md) | IMPLEMENTED |
| `apps/api/bin/start.sh` | Backend / DevOps | PORT-aware Gunicorn startup | [`per-file/apps/api/bin/start.sh.md`](per-file/apps/api/bin/start.sh.md) | IMPLEMENTED |
| `apps/api/railway.json` | Backend / DevOps | Railway Docker build, pre-deploy migration, start command and readiness healthcheck | [`per-file/apps/api/railway.json.md`](per-file/apps/api/railway.json.md) | IMPLEMENTED |
| `apps/api/config/__init__.py` | Backend | Configuration package marker | [`per-file/apps/api/config/__init__.py.md`](per-file/apps/api/config/__init__.py.md) | IMPLEMENTED |
| `apps/api/config/asgi.py` | Backend | ASGI entrypoint for Django | [`per-file/apps/api/config/asgi.py.md`](per-file/apps/api/config/asgi.py.md) | IMPLEMENTED |
| `apps/api/config/settings.py` | Backend | Environment-driven Django settings, Railway host/origin handling, structured logging and fail-fast production validation | [`per-file/apps/api/config/settings.py.md`](per-file/apps/api/config/settings.py.md) | TESTED |
| `apps/api/config/settings_test.py` | Backend | Isolated PostgreSQL test settings used by pytest | [`per-file/apps/api/config/settings_test.py.md`](per-file/apps/api/config/settings_test.py.md) | TESTED |
| `apps/api/config/urls.py` | Backend | Root URL map for health, API v1 and JSON error handlers | [`per-file/apps/api/config/urls.py.md`](per-file/apps/api/config/urls.py.md) | TESTED |
| `apps/api/config/wsgi.py` | Backend | WSGI entrypoint used by Gunicorn | [`per-file/apps/api/config/wsgi.py.md`](per-file/apps/api/config/wsgi.py.md) | IMPLEMENTED |
| `apps/api/corn/__init__.py` | Backend | Django application package marker | [`per-file/apps/api/corn/__init__.py.md`](per-file/apps/api/corn/__init__.py.md) | IMPLEMENTED |
| `apps/api/corn/apps.py` | Backend | Django app configuration | [`per-file/apps/api/corn/apps.py.md`](per-file/apps/api/corn/apps.py.md) | IMPLEMENTED |
| `apps/api/corn/auth.py` | Backend | DRF session authentication and role permission classes | [`per-file/apps/api/corn/auth.py.md`](per-file/apps/api/corn/auth.py.md) | TESTED |
| `apps/api/corn/enums.py` | Backend | Canonical TextChoices values shared by models, services and serializers | [`per-file/apps/api/corn/enums.py.md`](per-file/apps/api/corn/enums.py.md) | TESTED |
| `apps/api/corn/errors.py` | Backend | Application exceptions, uniform JSON error envelope and DRF/Django error handling | [`per-file/apps/api/corn/errors.py.md`](per-file/apps/api/corn/errors.py.md) | TESTED |
| `apps/api/corn/geo.py` | Backend | Geodesic distance and captured-location metadata; no location warnings or approval gate | [`per-file/apps/api/corn/geo.py.md`](per-file/apps/api/corn/geo.py.md) | TESTED |
| `apps/api/corn/management/__init__.py` | Backend | Management command package marker | [`per-file/apps/api/corn/management/__init__.py.md`](per-file/apps/api/corn/management/__init__.py.md) | IMPLEMENTED |
| `apps/api/corn/management/commands/__init__.py` | Backend | Management command package marker | [`per-file/apps/api/corn/management/commands/__init__.py.md`](per-file/apps/api/corn/management/commands/__init__.py.md) | IMPLEMENTED |
| `apps/api/corn/management/commands/create_admin.py` | Backend | One-time first-administrator bootstrap command | [`per-file/apps/api/corn/management/commands/create_admin.py.md`](per-file/apps/api/corn/management/commands/create_admin.py.md) | TESTED |
| `apps/api/corn/management/commands/issue_password_reset.py` | Backend | Operator-only one-time password-reset link issuance | [`per-file/apps/api/corn/management/commands/issue_password_reset.py.md`](per-file/apps/api/corn/management/commands/issue_password_reset.py.md) | IMPLEMENTED |
| `apps/api/corn/middleware.py` | Backend | Request ID and safe security response middleware | [`per-file/apps/api/corn/middleware.py.md`](per-file/apps/api/corn/middleware.py.md) | TESTED |
| `apps/api/corn/migrations/0001_initial.py` | Backend | Initial Django schema, constraints and indexes | [`per-file/apps/api/corn/migrations/0001_initial.py.md`](per-file/apps/api/corn/migrations/0001_initial.py.md) | TESTED |
| `apps/api/corn/migrations/0002_append_only_triggers.py` | Backend | PostgreSQL triggers that make stock movements and audit events append-only | [`per-file/apps/api/corn/migrations/0002_append_only_triggers.py.md`](per-file/apps/api/corn/migrations/0002_append_only_triggers.py.md) | TESTED |
| `apps/api/corn/migrations/0003_campaign_sites_optional_location.py` | Backend | Adds campaign-scoped sites, nullable coordinates and assignment-based campaign backfill | [`per-file/apps/api/corn/migrations/0003_campaign_sites_optional_location.py.md`](per-file/apps/api/corn/migrations/0003_campaign_sites_optional_location.py.md) | TESTED |
| `apps/api/corn/migrations/0004_scoped_idempotency_and_reversals.py` | Backend | Scopes legacy idempotency keys, adds reversal/review columns and recreates the append-only trigger transactionally | [`per-file/apps/api/corn/migrations/0004_scoped_idempotency_and_reversals.py.md`](per-file/apps/api/corn/migrations/0004_scoped_idempotency_and_reversals.py.md) | TESTED |
| `apps/api/corn/migrations/__init__.py` | Backend | Django migrations package marker | [`per-file/apps/api/corn/migrations/__init__.py.md`](per-file/apps/api/corn/migrations/__init__.py.md) | IMPLEMENTED |
| `apps/api/corn/models.py` | Backend | Django ORM schema, constraints, indexes and append-only table mappings | [`per-file/apps/api/corn/models.py.md`](per-file/apps/api/corn/models.py.md) | TESTED |
| `apps/api/corn/presenters.py` | Backend | Canonical JSON response shaping, including site/distributor display fields | [`per-file/apps/api/corn/presenters.py.md`](per-file/apps/api/corn/presenters.py.md) | TESTED |
| `apps/api/corn/rate_limit.py` | Backend | Memory-bounded process-local rate limiting for authentication attempts; shared limiter required for multi-worker scale-out | [`per-file/apps/api/corn/rate_limit.py.md`](per-file/apps/api/corn/rate_limit.py.md) | TESTED |
| `apps/api/corn/security.py` | Backend | Argon2id password handling, token hashing and HMAC signing helpers | [`per-file/apps/api/corn/security.py.md`](per-file/apps/api/corn/security.py.md) | TESTED |
| `apps/api/corn/serializers.py` | Backend | Strict DRF input serializers for every mutation boundary | [`per-file/apps/api/corn/serializers.py.md`](per-file/apps/api/corn/serializers.py.md) | TESTED |
| `apps/api/corn/services/__init__.py` | Backend | Service package marker | [`per-file/apps/api/corn/services/__init__.py.md`](per-file/apps/api/corn/services/__init__.py.md) | IMPLEMENTED |
| `apps/api/corn/services/analytics.py` | Backend | Dashboard, distributor/site analytics, delivery-point map data, legacy map-site data, non-location integrity flag counts and CSV calculations | [`per-file/apps/api/corn/services/analytics.py.md`](per-file/apps/api/corn/services/analytics.py.md) | TESTED |
| `apps/api/corn/services/audit.py` | Backend | Append-only audit writer and request-context extraction | [`per-file/apps/api/corn/services/audit.py.md`](per-file/apps/api/corn/services/audit.py.md) | TESTED |
| `apps/api/corn/services/auth.py` | Backend | Login, invitation, password reset/change, session revocation and account lifecycle | [`per-file/apps/api/corn/services/auth.py.md`](per-file/apps/api/corn/services/auth.py.md) | TESTED |
| `apps/api/corn/services/campaigns.py` | Backend | Campaigns, sites and distributor assignment domain rules | [`per-file/apps/api/corn/services/campaigns.py.md`](per-file/apps/api/corn/services/campaigns.py.md) | TESTED |
| `apps/api/corn/services/distribution.py` | Backend | Delivery submission, manual approval from any recorded place, evidence-integrity override and idempotent record transitions | [`per-file/apps/api/corn/services/distribution.py.md`](per-file/apps/api/corn/services/distribution.py.md) | TESTED |
| `apps/api/corn/services/evidence.py` | Backend | Upload intents, image validation, non-location integrity flags, evidence persistence and private view authorization | [`per-file/apps/api/corn/services/evidence.py.md`](per-file/apps/api/corn/services/evidence.py.md) | TESTED |
| `apps/api/corn/services/inventory.py` | Backend | Double-entry ledger, postings, reservations, reversals and derived balances | [`per-file/apps/api/corn/services/inventory.py.md`](per-file/apps/api/corn/services/inventory.py.md) | TESTED |
| `apps/api/corn/services/settings.py` | Backend | Organization settings read/update rules and unit validation | [`per-file/apps/api/corn/services/settings.py.md`](per-file/apps/api/corn/services/settings.py.md) | TESTED |
| `apps/api/corn/storage.py` | Backend | Private local/S3 evidence storage, virtual-host addressing, short-lived signed URLs and health probes | [`per-file/apps/api/corn/storage.py.md`](per-file/apps/api/corn/storage.py.md) | TESTED |
| `apps/api/corn/units.py` | Backend | Decimal kg conversion and display-unit helpers | [`per-file/apps/api/corn/units.py.md`](per-file/apps/api/corn/units.py.md) | TESTED |
| `apps/api/corn/views/__init__.py` | Backend | View package marker | [`per-file/apps/api/corn/views/__init__.py.md`](per-file/apps/api/corn/views/__init__.py.md) | IMPLEMENTED |
| `apps/api/corn/views/analytics.py` | Backend | Analytics endpoints, delivery-point map and audited CSV export | [`per-file/apps/api/corn/views/analytics.py.md`](per-file/apps/api/corn/views/analytics.py.md) | TESTED |
| `apps/api/corn/views/assignments.py` | Backend | Distributor assignment endpoints | [`per-file/apps/api/corn/views/assignments.py.md`](per-file/apps/api/corn/views/assignments.py.md) | TESTED |
| `apps/api/corn/views/auth.py` | Backend | Session login/logout, CSRF bootstrap, invitations and password lifecycle endpoints | [`per-file/apps/api/corn/views/auth.py.md`](per-file/apps/api/corn/views/auth.py.md) | TESTED |
| `apps/api/corn/views/campaigns.py` | Backend | Campaign endpoints | [`per-file/apps/api/corn/views/campaigns.py.md`](per-file/apps/api/corn/views/campaigns.py.md) | TESTED |
| `apps/api/corn/views/deliveries.py` | Backend | Distributor submission and admin review endpoints | [`per-file/apps/api/corn/views/deliveries.py.md`](per-file/apps/api/corn/views/deliveries.py.md) | TESTED |
| `apps/api/corn/views/evidence.py` | Backend | Evidence intent, upload, signed view and blob endpoints | [`per-file/apps/api/corn/views/evidence.py.md`](per-file/apps/api/corn/views/evidence.py.md) | TESTED |
| `apps/api/corn/views/health.py` | Backend | Unauthenticated liveness and readiness probes | [`per-file/apps/api/corn/views/health.py.md`](per-file/apps/api/corn/views/health.py.md) | TESTED |
| `apps/api/corn/views/helpers.py` | Backend | Shared view helpers for request data, CSRF cookies, pagination and JSON shapes | [`per-file/apps/api/corn/views/helpers.py.md`](per-file/apps/api/corn/views/helpers.py.md) | TESTED |
| `apps/api/corn/views/inventory.py` | Backend | Inventory receipt, allocation, adjustment, reversal and ledger endpoints | [`per-file/apps/api/corn/views/inventory.py.md`](per-file/apps/api/corn/views/inventory.py.md) | TESTED |
| `apps/api/corn/views/settings.py` | Backend | Organization settings endpoints | [`per-file/apps/api/corn/views/settings.py.md`](per-file/apps/api/corn/views/settings.py.md) | TESTED |
| `apps/api/corn/views/sites.py` | Backend | Site management and progress endpoints | [`per-file/apps/api/corn/views/sites.py.md`](per-file/apps/api/corn/views/sites.py.md) | TESTED |
| `apps/api/corn/views/users.py` | Backend | Distributor management endpoints | [`per-file/apps/api/corn/views/users.py.md`](per-file/apps/api/corn/views/users.py.md) | TESTED |
| `apps/api/manage.py` | Backend | Django management entrypoint | [`per-file/apps/api/manage.py.md`](per-file/apps/api/manage.py.md) | TESTED |
| `apps/api/pyproject.toml` | Backend | Python/Ruff/mypy/Django-stubs project configuration | [`per-file/apps/api/pyproject.toml.md`](per-file/apps/api/pyproject.toml.md) | TESTED |
| `apps/api/pytest.ini` | Backend | Pytest Django settings configuration | [`per-file/apps/api/pytest.ini.md`](per-file/apps/api/pytest.ini.md) | TESTED |
| `apps/api/requirements-dev.txt` | Backend | Pinned development/test dependencies | [`per-file/apps/api/requirements-dev.txt.md`](per-file/apps/api/requirements-dev.txt.md) | TESTED |
| `apps/api/requirements.txt` | Backend | Pinned runtime dependencies | [`per-file/apps/api/requirements.txt.md`](per-file/apps/api/requirements.txt.md) | TESTED |


## Backend tests

| Target file | Owner | Responsibility | Handoff note | Status |
|---|---|---|---|---|
| `apps/api/tests/__init__.py` | Backend | Backend test package marker | [`per-file/apps/api/tests/__init__.py.md`](per-file/apps/api/tests/__init__.py.md) | IMPLEMENTED |
| `apps/api/tests/conftest.py` | Backend | Backend fixtures for temporary databases, session/CSRF clients, tenant world and synthetic uploads | [`per-file/apps/api/tests/conftest.py.md`](per-file/apps/api/tests/conftest.py.md) | TESTED |
| `apps/api/tests/test_analytics_scope.py` | Backend | Analytics scope, denominators, delivery-map coverage and export authorization tests | [`per-file/apps/api/tests/test_analytics_scope.py.md`](per-file/apps/api/tests/test_analytics_scope.py.md) | TESTED |
| `apps/api/tests/test_auth_permissions.py` | Backend | Session auth, CSRF, RBAC, invitation/reset and ownership tests | [`per-file/apps/api/tests/test_auth_permissions.py.md`](per-file/apps/api/tests/test_auth_permissions.py.md) | TESTED |
| `apps/api/tests/test_campaign_sites.py` | Backend | Campaign site creation, generated codes, optional/cleared locations, duplicate-name (including rename), cross-campaign assignment and analytics-scoping tests | [`per-file/apps/api/tests/test_campaign_sites.py.md`](per-file/apps/api/tests/test_campaign_sites.py.md) | TESTED |
| `apps/api/tests/test_config_security.py` | Backend | Production/staging configuration fail-fast tests | [`per-file/apps/api/tests/test_config_security.py.md`](per-file/apps/api/tests/test_config_security.py.md) | TESTED |
| `apps/api/tests/test_distribution_submission.py` | Backend | Submission, review transitions, location-independent approval, idempotency and evidence validation tests | [`per-file/apps/api/tests/test_distribution_submission.py.md`](per-file/apps/api/tests/test_distribution_submission.py.md) | TESTED |
| `apps/api/tests/test_geotag_validation.py` | Backend | Location capture, no-warning behavior and non-location evidence-integrity tests | [`per-file/apps/api/tests/test_geotag_validation.py.md`](per-file/apps/api/tests/test_geotag_validation.py.md) | TESTED |
| `apps/api/tests/test_inventory_ledger.py` | Backend | Ledger postings, reservations, reversals, append-only triggers and concurrency tests | [`per-file/apps/api/tests/test_inventory_ledger.py.md`](per-file/apps/api/tests/test_inventory_ledger.py.md) | TESTED |
| `apps/api/tests/test_remediation_regressions.py` | Backend | Audit regressions: scoped/legacy idempotency, reservations, reversal integrity, target locking, scope leaks, evidence tamper/oversize, proxy trust and limiter bounds | [`per-file/apps/api/tests/test_remediation_regressions.py.md`](per-file/apps/api/tests/test_remediation_regressions.py.md) | TESTED |

## Frontend application

| Target file | Owner | Responsibility | Handoff note | Status |
|---|---|---|---|---|
| `apps/web/src/App.tsx` | Frontend | Application shell | [`per-file/apps/web/src/App.tsx.md`](per-file/apps/web/src/App.tsx.md) | IMPLEMENTED |
| `apps/web/src/app/providers.tsx` | Frontend | App providers | [`per-file/apps/web/src/app/providers.tsx.md`](per-file/apps/web/src/app/providers.tsx.md) | IMPLEMENTED |
| `apps/web/src/app/router.tsx` | Frontend | Routes and guards | [`per-file/apps/web/src/app/router.tsx.md`](per-file/apps/web/src/app/router.tsx.md) | IMPLEMENTED |
| `apps/web/src/components/common/ConfirmDialog.tsx` | Frontend | Confirmation dialog | [`per-file/apps/web/src/components/common/ConfirmDialog.tsx.md`](per-file/apps/web/src/components/common/ConfirmDialog.tsx.md) | IMPLEMENTED |
| `apps/web/src/components/common/DataTable.tsx` | Frontend | Reusable accessible table | [`per-file/apps/web/src/components/common/DataTable.tsx.md`](per-file/apps/web/src/components/common/DataTable.tsx.md) | IMPLEMENTED |
| `apps/web/src/components/common/EmptyState.tsx` | Frontend | Empty state | [`per-file/apps/web/src/components/common/EmptyState.tsx.md`](per-file/apps/web/src/components/common/EmptyState.tsx.md) | IMPLEMENTED |
| `apps/web/src/components/common/ErrorState.tsx` | Frontend | Error state | [`per-file/apps/web/src/components/common/ErrorState.tsx.md`](per-file/apps/web/src/components/common/ErrorState.tsx.md) | IMPLEMENTED |
| `apps/web/src/components/common/FormField.tsx` | Frontend | Form field wrapper | [`per-file/apps/web/src/components/common/FormField.tsx.md`](per-file/apps/web/src/components/common/FormField.tsx.md) | IMPLEMENTED |
| `apps/web/src/components/common/MapCanvas.tsx` | Frontend | Shared MapLibre street/satellite canvas with accessible markers, locate control and fallback | [`per-file/apps/web/src/components/common/MapCanvas.tsx.md`](per-file/apps/web/src/components/common/MapCanvas.tsx.md) | IMPLEMENTED |
| `apps/web/src/components/common/StatCard.tsx` | Frontend | KPI card | [`per-file/apps/web/src/components/common/StatCard.tsx.md`](per-file/apps/web/src/components/common/StatCard.tsx.md) | IMPLEMENTED |
| `apps/web/src/components/common/StatusBadge.tsx` | Frontend | Status display | [`per-file/apps/web/src/components/common/StatusBadge.tsx.md`](per-file/apps/web/src/components/common/StatusBadge.tsx.md) | IMPLEMENTED |
| `apps/web/src/components/layout/AppShell.tsx` | Frontend | Role-aware layout | [`per-file/apps/web/src/components/layout/AppShell.tsx.md`](per-file/apps/web/src/components/layout/AppShell.tsx.md) | IMPLEMENTED |
| `apps/web/src/components/layout/Sidebar.tsx` | Frontend | Navigation sidebar | [`per-file/apps/web/src/components/layout/Sidebar.tsx.md`](per-file/apps/web/src/components/layout/Sidebar.tsx.md) | IMPLEMENTED |
| `apps/web/src/components/layout/TopBar.tsx` | Frontend | Top bar | [`per-file/apps/web/src/components/layout/TopBar.tsx.md`](per-file/apps/web/src/components/layout/TopBar.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/admin/analytics/AnalyticsPage.tsx` | Frontend | Analytics and exports | [`per-file/apps/web/src/features/admin/analytics/AnalyticsPage.tsx.md`](per-file/apps/web/src/features/admin/analytics/AnalyticsPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/admin/audit/AuditTrailPage.tsx` | Frontend | Audit trail UI | [`per-file/apps/web/src/features/admin/audit/AuditTrailPage.tsx.md`](per-file/apps/web/src/features/admin/audit/AuditTrailPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/admin/campaigns/CampaignsPage.test.tsx` | Frontend | Campaign site setup, name-only add and optional-location tests | [`per-file/apps/web/src/features/admin/campaigns/CampaignsPage.test.tsx.md`](per-file/apps/web/src/features/admin/campaigns/CampaignsPage.test.tsx.md) | TESTED |
| `apps/web/src/features/admin/campaigns/CampaignsPage.tsx` | Frontend | Campaigns, campaign-scoped sites and assignment planner | [`per-file/apps/web/src/features/admin/campaigns/CampaignsPage.tsx.md`](per-file/apps/web/src/features/admin/campaigns/CampaignsPage.tsx.md) | TESTED |
| `apps/web/src/features/admin/dashboard/AdminDashboardPage.tsx` | Frontend | Admin overview | [`per-file/apps/web/src/features/admin/dashboard/AdminDashboardPage.tsx.md`](per-file/apps/web/src/features/admin/dashboard/AdminDashboardPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/admin/distributors/DistributorsPage.tsx` | Frontend | Distributor management | [`per-file/apps/web/src/features/admin/distributors/DistributorsPage.tsx.md`](per-file/apps/web/src/features/admin/distributors/DistributorsPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/admin/evidence/EvidenceReviewPage.tsx` | Frontend | Evidence review UI with location capture context, non-location integrity flags and street/satellite map links | [`per-file/apps/web/src/features/admin/evidence/EvidenceReviewPage.tsx.md`](per-file/apps/web/src/features/admin/evidence/EvidenceReviewPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/admin/inventory/InventoryPage.tsx` | Frontend | Inventory and ledger UI | [`per-file/apps/web/src/features/admin/inventory/InventoryPage.tsx.md`](per-file/apps/web/src/features/admin/inventory/InventoryPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/admin/map/DistributionMapPage.tsx` | Frontend | Delivery-only admin map with street/satellite, synchronized delivery list and record drawer | [`per-file/apps/web/src/features/admin/map/DistributionMapPage.tsx.md`](per-file/apps/web/src/features/admin/map/DistributionMapPage.tsx.md) | TESTED |
| `apps/web/src/features/admin/map/DistributionMapPage.test.tsx` | Frontend | Delivery-only map list, drawer and empty-state tests | [`per-file/apps/web/src/features/admin/map/DistributionMapPage.test.tsx.md`](per-file/apps/web/src/features/admin/map/DistributionMapPage.test.tsx.md) | TESTED |
| `apps/web/src/features/admin/settings/SettingsPage.tsx` | Frontend | Settings (timezone/unit/bag/capture drift) and audit UI; legacy location thresholds not editable | [`per-file/apps/web/src/features/admin/settings/SettingsPage.tsx.md`](per-file/apps/web/src/features/admin/settings/SettingsPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/admin/shared/flags.tsx` | Frontend | Shared non-location evidence-integrity flag and captured/missing location UI | [`per-file/apps/web/src/features/admin/shared/flags.tsx.md`](per-file/apps/web/src/features/admin/shared/flags.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/auth/AuthLayout.tsx` | Frontend | Shared split layout for public authentication screens. | [`per-file/apps/web/src/features/auth/AuthLayout.tsx.md`](per-file/apps/web/src/features/auth/AuthLayout.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/auth/LoginPage.test.tsx` | Frontend | Login failure-message and rate-limit UX tests | [`per-file/apps/web/src/features/auth/LoginPage.test.tsx.md`](per-file/apps/web/src/features/auth/LoginPage.test.tsx.md) | TESTED |
| `apps/web/src/features/auth/LoginPage.tsx` | Frontend | Login page with actionable throttle/outage errors | [`per-file/apps/web/src/features/auth/LoginPage.tsx.md`](per-file/apps/web/src/features/auth/LoginPage.tsx.md) | TESTED |
| `apps/web/src/features/auth/PasswordResetPage.tsx` | Frontend | Password reset UI | [`per-file/apps/web/src/features/auth/PasswordResetPage.tsx.md`](per-file/apps/web/src/features/auth/PasswordResetPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/distributor/dashboard/DistributorDashboardPage.tsx` | Frontend | Distributor home | [`per-file/apps/web/src/features/distributor/dashboard/DistributorDashboardPage.tsx.md`](per-file/apps/web/src/features/distributor/dashboard/DistributorDashboardPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/distributor/deliveries/DeliverySubmissionPage.test.tsx` | Frontend | Delivery workflow tests | [`per-file/apps/web/src/features/distributor/deliveries/DeliverySubmissionPage.test.tsx.md`](per-file/apps/web/src/features/distributor/deliveries/DeliverySubmissionPage.test.tsx.md) | TESTED |
| `apps/web/src/features/distributor/deliveries/DeliverySubmissionPage.tsx` | Frontend | Delivery form workflow | [`per-file/apps/web/src/features/distributor/deliveries/DeliverySubmissionPage.tsx.md`](per-file/apps/web/src/features/distributor/deliveries/DeliverySubmissionPage.tsx.md) | TESTED |
| `apps/web/src/features/distributor/deliveries/MySubmissionsPage.tsx` | Frontend | Distributor submission history | [`per-file/apps/web/src/features/distributor/deliveries/MySubmissionsPage.tsx.md`](per-file/apps/web/src/features/distributor/deliveries/MySubmissionsPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/distributor/evidence/PhotoCapturePanel.tsx` | Frontend | Photo capture UI | [`per-file/apps/web/src/features/distributor/evidence/PhotoCapturePanel.tsx.md`](per-file/apps/web/src/features/distributor/evidence/PhotoCapturePanel.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/distributor/evidence/useDeviceLocation.ts` | Frontend | Geolocation hook | [`per-file/apps/web/src/features/distributor/evidence/useDeviceLocation.ts.md`](per-file/apps/web/src/features/distributor/evidence/useDeviceLocation.ts.md) | TESTED |
| `apps/web/src/features/distributor/offline/DraftsSyncPage.tsx` | Frontend | Distributor drafts and sync queue screen. | [`per-file/apps/web/src/features/distributor/offline/DraftsSyncPage.tsx.md`](per-file/apps/web/src/features/distributor/offline/DraftsSyncPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/distributor/offline/offlineQueue.ts` | Frontend | Offline draft queue | [`per-file/apps/web/src/features/distributor/offline/offlineQueue.ts.md`](per-file/apps/web/src/features/distributor/offline/offlineQueue.ts.md) | TESTED |
| `apps/web/src/features/distributor/sites/AssignedSitesPage.tsx` | Frontend | Assigned sites list | [`per-file/apps/web/src/features/distributor/sites/AssignedSitesPage.tsx.md`](per-file/apps/web/src/features/distributor/sites/AssignedSitesPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/distributor/sites/SiteDetailPage.tsx` | Frontend | Assigned site detail | [`per-file/apps/web/src/features/distributor/sites/SiteDetailPage.tsx.md`](per-file/apps/web/src/features/distributor/sites/SiteDetailPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/lib/api-client.test.ts` | Frontend | API client session/CSRF tests. | [`per-file/apps/web/src/lib/api-client.test.ts.md`](per-file/apps/web/src/lib/api-client.test.ts.md) | TESTED |
| `apps/web/src/lib/api-client.ts` | Frontend | Typed API client over Django session auth and CSRF. | [`per-file/apps/web/src/lib/api-client.ts.md`](per-file/apps/web/src/lib/api-client.ts.md) | TESTED |
| `apps/web/src/lib/format.ts` | Frontend | Shared formatting helpers | [`per-file/apps/web/src/lib/format.ts.md`](per-file/apps/web/src/lib/format.ts.md) | IMPLEMENTED |
| `apps/web/src/lib/map.test.ts` | Frontend | Street/satellite basemap resolution and OSM/Google Maps link tests | [`per-file/apps/web/src/lib/map.test.ts.md`](per-file/apps/web/src/lib/map.test.ts.md) | TESTED |
| `apps/web/src/lib/map.ts` | Frontend | OpenStreetMap + Esri satellite style, tile/style overrides, OSM/Google Maps links | [`per-file/apps/web/src/lib/map.ts.md`](per-file/apps/web/src/lib/map.ts.md) | TESTED |
| `apps/web/src/lib/permissions.test.ts` | Frontend | Permission helper tests | [`per-file/apps/web/src/lib/permissions.test.ts.md`](per-file/apps/web/src/lib/permissions.test.ts.md) | TESTED |
| `apps/web/src/lib/permissions.ts` | Frontend | UI permissions | [`per-file/apps/web/src/lib/permissions.ts.md`](per-file/apps/web/src/lib/permissions.ts.md) | TESTED |
| `apps/web/src/lib/query-client.ts` | Frontend | Server state cache | [`per-file/apps/web/src/lib/query-client.ts.md`](per-file/apps/web/src/lib/query-client.ts.md) | IMPLEMENTED |
| `apps/web/src/lib/session.ts` | Frontend | Session state for Django cookie authentication. | [`per-file/apps/web/src/lib/session.ts.md`](per-file/apps/web/src/lib/session.ts.md) | TESTED |
| `apps/web/src/main.tsx` | Frontend | Web entrypoint | [`per-file/apps/web/src/main.tsx.md`](per-file/apps/web/src/main.tsx.md) | IMPLEMENTED |
| `apps/web/src/styles/global.css` | Frontend | Global styles | [`per-file/apps/web/src/styles/global.css.md`](per-file/apps/web/src/styles/global.css.md) | IMPLEMENTED |
| `apps/web/src/styles/tokens.css` | Frontend | Design tokens | [`per-file/apps/web/src/styles/tokens.css.md`](per-file/apps/web/src/styles/tokens.css.md) | IMPLEMENTED |
| `apps/web/src/types/domain.ts` | Frontend | Shared web domain types | [`per-file/apps/web/src/types/domain.ts.md`](per-file/apps/web/src/types/domain.ts.md) | IMPLEMENTED |

## Web build, tests and E2E

| Target file | Owner | Responsibility | Handoff note | Status |
|---|---|---|---|---|
| `apps/web/.dockerignore` | Frontend/DevOps | Container build-context filter; retained but outside the supported native workflow | [`per-file/apps/web/.dockerignore.md`](per-file/apps/web/.dockerignore.md) | DEFERRED |
| `apps/web/Dockerfile` | Frontend/DevOps | Multi-stage web container; statically validated, runtime build deferred | [`per-file/apps/web/Dockerfile.md`](per-file/apps/web/Dockerfile.md) | IMPLEMENTED |
| `apps/web/e2e/distribution.spec.ts` | QA | Critical distributor/reviewer browser workflow including the delivery-only admin map. | [`per-file/apps/web/e2e/distribution.spec.ts.md`](per-file/apps/web/e2e/distribution.spec.ts.md) | TESTED |
| `apps/web/e2e/global-setup.ts` | QA | Per-run credentials and first-admin bootstrap for Playwright. | [`per-file/apps/web/e2e/global-setup.ts.md`](per-file/apps/web/e2e/global-setup.ts.md) | TESTED |
| `apps/web/e2e/setup.spec.ts` | QA | E2E data seeding through public APIs | [`per-file/apps/web/e2e/setup.spec.ts.md`](per-file/apps/web/e2e/setup.spec.ts.md) | TESTED |
| `apps/web/e2e/support/config.ts` | QA | Shared E2E identifiers and fixture bytes | [`per-file/apps/web/e2e/support/config.ts.md`](per-file/apps/web/e2e/support/config.ts.md) | TESTED |
| `apps/web/e2e/support/credentials.ts` | QA | Per-run E2E credential reader | [`per-file/apps/web/e2e/support/credentials.ts.md`](per-file/apps/web/e2e/support/credentials.ts.md) | TESTED |
| `apps/web/e2e/support/prepare_db.py` | QA | Recreate only the disposable E2E PostgreSQL database. | [`per-file/apps/web/e2e/support/prepare_db.py.md`](per-file/apps/web/e2e/support/prepare_db.py.md) | TESTED |
| `apps/web/e2e/support/run-e2e.mjs` | QA | Prepare the disposable Django E2E database before Playwright starts web servers. | [`per-file/apps/web/e2e/support/run-e2e.mjs.md`](per-file/apps/web/e2e/support/run-e2e.mjs.md) | TESTED |
| `apps/web/eslint.config.js` | Frontend/DevOps | ESLint flat config | [`per-file/apps/web/eslint.config.js.md`](per-file/apps/web/eslint.config.js.md) | TESTED |
| `apps/web/index.html` | Frontend/DevOps | Web HTML shell | [`per-file/apps/web/index.html.md`](per-file/apps/web/index.html.md) | IMPLEMENTED |
| `apps/web/nginx.conf` | Frontend/DevOps | SPA server with same-origin API proxy, CSP/COOP/frame headers and overwritten forwarding headers. | [`per-file/apps/web/nginx.conf.md`](per-file/apps/web/nginx.conf.md) | IMPLEMENTED |
| `apps/web/nginx.docker.conf` | Frontend/DevOps | Container nginx config using the Compose `api` upstream and static SPA root; statically validated, runtime test deferred. | [`per-file/apps/web/nginx.docker.conf.md`](per-file/apps/web/nginx.docker.conf.md) | IMPLEMENTED |
| `apps/web/package-lock.json` | Frontend/DevOps | Reproducible npm dependency lockfile | [`per-file/apps/web/package-lock.json.md`](per-file/apps/web/package-lock.json.md) | TESTED |
| `apps/web/package.json` | Frontend/DevOps | Web scripts/dependencies | [`per-file/apps/web/package.json.md`](per-file/apps/web/package.json.md) | TESTED |
| `apps/web/playwright.config.ts` | QA | Browser E2E orchestration. | [`per-file/apps/web/playwright.config.ts.md`](per-file/apps/web/playwright.config.ts.md) | TESTED |
| `apps/web/tsconfig.json` | Frontend/DevOps | TypeScript config | [`per-file/apps/web/tsconfig.json.md`](per-file/apps/web/tsconfig.json.md) | TESTED |
| `apps/web/scripts/check-deploy-config.mjs` | Frontend/DevOps | Fail Vercel builds while the Railway proxy placeholder remains | [`per-file/apps/web/scripts/check-deploy-config.mjs.md`](per-file/apps/web/scripts/check-deploy-config.mjs.md) | IMPLEMENTED |
| `apps/web/vercel.json` | Frontend/DevOps | Vercel Vite build, same-origin `/api` rewrite, uncached API responses, SPA fallback and security headers | [`per-file/apps/web/vercel.json.md`](per-file/apps/web/vercel.json.md) | IMPLEMENTED |
| `apps/web/vite.config.ts` | Frontend/DevOps | Vite config | [`per-file/apps/web/vite.config.ts.md`](per-file/apps/web/vite.config.ts.md) | TESTED |
| `apps/web/vitest.setup.ts` | Frontend/DevOps | Vitest setup | [`per-file/apps/web/vitest.setup.ts.md`](per-file/apps/web/vitest.setup.ts.md) | TESTED |

## Repository and deployment

| Target file | Owner | Responsibility | Handoff note | Status |
|---|---|---|---|---|
| `.env.example` | DevOps/Lead | Configuration template including Railway/Vercel production placeholders | [`per-file/.env.example.md`](per-file/.env.example.md) | IMPLEMENTED |
| `.github/dependabot.yml` | DevOps/Lead | Weekly dependency updates for pip/npm and monthly GitHub Actions updates | [`per-file/.github/dependabot.yml.md`](per-file/.github/dependabot.yml.md) | IMPLEMENTED |
| `.github/workflows/ci.yml` | DevOps/Lead | Backend, frontend, Playwright E2E and dependency-review CI jobs; YAML-validated, not yet executed on GitHub | [`per-file/.github/workflows/ci.yml.md`](per-file/.github/workflows/ci.yml.md) | IMPLEMENTED |
| `AGENTS.md` | DevOps/Lead | Project file: AGENTS.md | [`per-file/AGENTS.md.md`](per-file/AGENTS.md.md) | IMPLEMENTED |
| `Makefile` | DevOps/Lead | Developer commands including the aggregate `make check` gate | [`per-file/Makefile.md`](per-file/Makefile.md) | TESTED |
| `README.md` | DevOps/Lead | Repository run and deployment guide | [`per-file/README.md.md`](per-file/README.md.md) | IMPLEMENTED |
| `docs/ops/RAILWAY_VERCEL_DEPLOYMENT.md` | DevOps/Lead | Managed Railway API/Postgres/Bucket and Vercel SPA deployment guide | [`per-file/docs/ops/RAILWAY_VERCEL_DEPLOYMENT.md.md`](per-file/docs/ops/RAILWAY_VERCEL_DEPLOYMENT.md.md) | IMPLEMENTED |
| `infra/railway-bucket-cors.json` | DevOps | S3 CORS policy for browser presigned evidence uploads | [`per-file/infra/railway-bucket-cors.json.md`](per-file/infra/railway-bucket-cors.json.md) | IMPLEMENTED |
| `docker-compose.yml` | DevOps/Lead | Container stack with nginx upstream, readiness healthcheck and service dependencies; statically validated, runtime build deferred | [`per-file/docker-compose.yml.md`](per-file/docker-compose.yml.md) | IMPLEMENTED |

## Removed files

| Target file | Owner | Responsibility | Handoff note | Status |
|---|---|---|---|---|
| `apps/web/src/features/admin/sites/SitesPage.tsx` | Frontend | Removed standalone admin Sites page; site creation and optional location editing now live in `CampaignsPage`. The `/sites` SPA route redirects to `/campaigns`. | [`per-file/apps/web/src/features/admin/sites/SitesPage.tsx.md`](per-file/apps/web/src/features/admin/sites/SitesPage.tsx.md) | REMOVED |
