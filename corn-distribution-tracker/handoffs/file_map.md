# File Map and Ownership

Status values: `PLANNED`, `IN_PROGRESS`, `IMPLEMENTED`, `TESTED`, `DEFERRED`. Initial status is `PLANNED` for all files. Each target file has a corresponding handoff note under `handoffs/per-file/`, with its target path repeated in the note.

| Target file | Owner | Responsibility | Handoff note | Status |
|---|---|---|---|---|
| `apps/api/app/main.py` | Backend | API entrypoint | [`per-file/apps/api/app/main.py.md`](per-file/apps/api/app/main.py.md) | TESTED |
| `apps/api/app/core/config.py` | Backend | Typed settings | [`per-file/apps/api/app/core/config.py.md`](per-file/apps/api/app/core/config.py.md) | TESTED |
| `apps/api/app/core/security.py` | Backend | Security primitives | [`per-file/apps/api/app/core/security.py.md`](per-file/apps/api/app/core/security.py.md) | TESTED |
| `apps/api/app/db/session.py` | Backend | DB session management | [`per-file/apps/api/app/db/session.py.md`](per-file/apps/api/app/db/session.py.md) | TESTED |
| `apps/api/app/db/base.py` | Backend | Model registry | [`per-file/apps/api/app/db/base.py.md`](per-file/apps/api/app/db/base.py.md) | TESTED |
| `apps/api/app/models/user.py` | Backend | User and auth session models | [`per-file/apps/api/app/models/user.py.md`](per-file/apps/api/app/models/user.py.md) | TESTED |
| `apps/api/app/models/campaign.py` | Backend | Campaign model | [`per-file/apps/api/app/models/campaign.py.md`](per-file/apps/api/app/models/campaign.py.md) | TESTED |
| `apps/api/app/models/distribution_site.py` | Backend | Site model | [`per-file/apps/api/app/models/distribution_site.py.md`](per-file/apps/api/app/models/distribution_site.py.md) | TESTED |
| `apps/api/app/models/distributor_assignment.py` | Backend | Assignment model | [`per-file/apps/api/app/models/distributor_assignment.py.md`](per-file/apps/api/app/models/distributor_assignment.py.md) | TESTED |
| `apps/api/app/models/stock_account.py` | Backend | Inventory account model | [`per-file/apps/api/app/models/stock_account.py.md`](per-file/apps/api/app/models/stock_account.py.md) | TESTED |
| `apps/api/app/models/stock_movement.py` | Backend | Append-only stock ledger model | [`per-file/apps/api/app/models/stock_movement.py.md`](per-file/apps/api/app/models/stock_movement.py.md) | TESTED |
| `apps/api/app/models/distribution_record.py` | Backend | Distribution submission model | [`per-file/apps/api/app/models/distribution_record.py.md`](per-file/apps/api/app/models/distribution_record.py.md) | TESTED |
| `apps/api/app/models/photo_evidence.py` | Backend | Evidence metadata model | [`per-file/apps/api/app/models/photo_evidence.py.md`](per-file/apps/api/app/models/photo_evidence.py.md) | TESTED |
| `apps/api/app/models/audit_event.py` | Backend | Audit trail model | [`per-file/apps/api/app/models/audit_event.py.md`](per-file/apps/api/app/models/audit_event.py.md) | TESTED |
| `apps/api/app/schemas/auth.py` | Backend | Auth request/response schemas | [`per-file/apps/api/app/schemas/auth.py.md`](per-file/apps/api/app/schemas/auth.py.md) | TESTED |
| `apps/api/app/schemas/users.py` | Backend | User schemas | [`per-file/apps/api/app/schemas/users.py.md`](per-file/apps/api/app/schemas/users.py.md) | TESTED |
| `apps/api/app/schemas/campaigns.py` | Backend | Campaign schemas | [`per-file/apps/api/app/schemas/campaigns.py.md`](per-file/apps/api/app/schemas/campaigns.py.md) | TESTED |
| `apps/api/app/schemas/sites.py` | Backend | Site schemas | [`per-file/apps/api/app/schemas/sites.py.md`](per-file/apps/api/app/schemas/sites.py.md) | TESTED |
| `apps/api/app/schemas/inventory.py` | Backend | Inventory schemas | [`per-file/apps/api/app/schemas/inventory.py.md`](per-file/apps/api/app/schemas/inventory.py.md) | TESTED |
| `apps/api/app/schemas/distributions.py` | Backend | Distribution schemas | [`per-file/apps/api/app/schemas/distributions.py.md`](per-file/apps/api/app/schemas/distributions.py.md) | TESTED |
| `apps/api/app/schemas/evidence.py` | Backend | Evidence schemas | [`per-file/apps/api/app/schemas/evidence.py.md`](per-file/apps/api/app/schemas/evidence.py.md) | TESTED |
| `apps/api/app/api/dependencies.py` | Backend | Auth/RBAC dependencies | [`per-file/apps/api/app/api/dependencies.py.md`](per-file/apps/api/app/api/dependencies.py.md) | TESTED |
| `apps/api/app/api/router.py` | Backend | API router registry | [`per-file/apps/api/app/api/router.py.md`](per-file/apps/api/app/api/router.py.md) | TESTED |
| `apps/api/app/api/routes/auth.py` | Backend | Auth endpoints | [`per-file/apps/api/app/api/routes/auth.py.md`](per-file/apps/api/app/api/routes/auth.py.md) | TESTED |
| `apps/api/app/api/routes/users.py` | Backend | Admin user routes | [`per-file/apps/api/app/api/routes/users.py.md`](per-file/apps/api/app/api/routes/users.py.md) | TESTED |
| `apps/api/app/api/routes/campaigns.py` | Backend | Campaign routes | [`per-file/apps/api/app/api/routes/campaigns.py.md`](per-file/apps/api/app/api/routes/campaigns.py.md) | TESTED |
| `apps/api/app/api/routes/sites.py` | Backend | Site routes | [`per-file/apps/api/app/api/routes/sites.py.md`](per-file/apps/api/app/api/routes/sites.py.md) | TESTED |
| `apps/api/app/api/routes/inventory.py` | Backend | Inventory endpoints | [`per-file/apps/api/app/api/routes/inventory.py.md`](per-file/apps/api/app/api/routes/inventory.py.md) | TESTED |
| `apps/api/app/api/routes/distributions.py` | Backend | Delivery endpoints | [`per-file/apps/api/app/api/routes/distributions.py.md`](per-file/apps/api/app/api/routes/distributions.py.md) | TESTED |
| `apps/api/app/api/routes/evidence.py` | Backend | Evidence endpoints | [`per-file/apps/api/app/api/routes/evidence.py.md`](per-file/apps/api/app/api/routes/evidence.py.md) | TESTED |
| `apps/api/app/api/routes/analytics.py` | Backend | Analytics endpoints | [`per-file/apps/api/app/api/routes/analytics.py.md`](per-file/apps/api/app/api/routes/analytics.py.md) | TESTED |
| `apps/api/app/services/auth_service.py` | Backend | Auth domain service | [`per-file/apps/api/app/services/auth_service.py.md`](per-file/apps/api/app/services/auth_service.py.md) | TESTED |
| `apps/api/app/services/inventory_service.py` | Backend | Ledger domain service | [`per-file/apps/api/app/services/inventory_service.py.md`](per-file/apps/api/app/services/inventory_service.py.md) | TESTED |
| `apps/api/app/services/distribution_service.py` | Backend | Submission/review service | [`per-file/apps/api/app/services/distribution_service.py.md`](per-file/apps/api/app/services/distribution_service.py.md) | TESTED |
| `apps/api/app/services/evidence_service.py` | Backend | Evidence processing service | [`per-file/apps/api/app/services/evidence_service.py.md`](per-file/apps/api/app/services/evidence_service.py.md) | TESTED |
| `apps/api/app/services/analytics_service.py` | Backend | Analytics calculations | [`per-file/apps/api/app/services/analytics_service.py.md`](per-file/apps/api/app/services/analytics_service.py.md) | TESTED |
| `apps/api/app/services/audit_service.py` | Backend | Audit writer | [`per-file/apps/api/app/services/audit_service.py.md`](per-file/apps/api/app/services/audit_service.py.md) | TESTED |
| `apps/api/app/services/storage_service.py` | Backend | Private object storage | [`per-file/apps/api/app/services/storage_service.py.md`](per-file/apps/api/app/services/storage_service.py.md) | TESTED |
| `apps/api/app/services/geo_service.py` | Backend | Geolocation calculations | [`per-file/apps/api/app/services/geo_service.py.md`](per-file/apps/api/app/services/geo_service.py.md) | TESTED |
| `apps/api/alembic/env.py` | Backend | Alembic environment | [`per-file/apps/api/alembic/env.py.md`](per-file/apps/api/alembic/env.py.md) | TESTED |
| `apps/api/alembic/versions/0001_initial_schema.py` | Backend | Initial schema migration | [`per-file/apps/api/alembic/versions/0001_initial_schema.py.md`](per-file/apps/api/alembic/versions/0001_initial_schema.py.md) | TESTED |
| `apps/api/tests/test_auth_permissions.py` | Backend | Auth/RBAC tests | [`per-file/apps/api/tests/test_auth_permissions.py.md`](per-file/apps/api/tests/test_auth_permissions.py.md) | TESTED |
| `apps/api/tests/test_inventory_ledger.py` | Backend | Ledger integrity tests | [`per-file/apps/api/tests/test_inventory_ledger.py.md`](per-file/apps/api/tests/test_inventory_ledger.py.md) | TESTED |
| `apps/api/tests/test_distribution_submission.py` | Backend | Distribution state tests | [`per-file/apps/api/tests/test_distribution_submission.py.md`](per-file/apps/api/tests/test_distribution_submission.py.md) | TESTED |
| `apps/api/tests/test_geotag_validation.py` | Backend | Geo/photo validation tests | [`per-file/apps/api/tests/test_geotag_validation.py.md`](per-file/apps/api/tests/test_geotag_validation.py.md) | TESTED |
| `apps/api/tests/test_analytics_scope.py` | Backend | Analytics tests | [`per-file/apps/api/tests/test_analytics_scope.py.md`](per-file/apps/api/tests/test_analytics_scope.py.md) | TESTED |
| `apps/web/src/main.tsx` | Frontend | Web entrypoint | [`per-file/apps/web/src/main.tsx.md`](per-file/apps/web/src/main.tsx.md) | IMPLEMENTED |
| `apps/web/src/App.tsx` | Frontend | Application shell | [`per-file/apps/web/src/App.tsx.md`](per-file/apps/web/src/App.tsx.md) | IMPLEMENTED |
| `apps/web/src/app/router.tsx` | Frontend | Routes and guards | [`per-file/apps/web/src/app/router.tsx.md`](per-file/apps/web/src/app/router.tsx.md) | IMPLEMENTED |
| `apps/web/src/app/providers.tsx` | Frontend | App providers | [`per-file/apps/web/src/app/providers.tsx.md`](per-file/apps/web/src/app/providers.tsx.md) | IMPLEMENTED |
| `apps/web/src/lib/api-client.ts` | Frontend | Typed API client | [`per-file/apps/web/src/lib/api-client.ts.md`](per-file/apps/web/src/lib/api-client.ts.md) | TESTED |
| `apps/web/src/lib/query-client.ts` | Frontend | Server state cache | [`per-file/apps/web/src/lib/query-client.ts.md`](per-file/apps/web/src/lib/query-client.ts.md) | IMPLEMENTED |
| `apps/web/src/lib/session.ts` | Frontend | Session state | [`per-file/apps/web/src/lib/session.ts.md`](per-file/apps/web/src/lib/session.ts.md) | IMPLEMENTED |
| `apps/web/src/lib/permissions.ts` | Frontend | UI permissions | [`per-file/apps/web/src/lib/permissions.ts.md`](per-file/apps/web/src/lib/permissions.ts.md) | TESTED |
| `apps/web/src/types/domain.ts` | Frontend | Shared web domain types | [`per-file/apps/web/src/types/domain.ts.md`](per-file/apps/web/src/types/domain.ts.md) | IMPLEMENTED |
| `apps/web/src/components/layout/AppShell.tsx` | Frontend | Role-aware layout | [`per-file/apps/web/src/components/layout/AppShell.tsx.md`](per-file/apps/web/src/components/layout/AppShell.tsx.md) | IMPLEMENTED |
| `apps/web/src/components/layout/Sidebar.tsx` | Frontend | Navigation sidebar | [`per-file/apps/web/src/components/layout/Sidebar.tsx.md`](per-file/apps/web/src/components/layout/Sidebar.tsx.md) | IMPLEMENTED |
| `apps/web/src/components/layout/TopBar.tsx` | Frontend | Top bar | [`per-file/apps/web/src/components/layout/TopBar.tsx.md`](per-file/apps/web/src/components/layout/TopBar.tsx.md) | IMPLEMENTED |
| `apps/web/src/components/common/StatCard.tsx` | Frontend | KPI card | [`per-file/apps/web/src/components/common/StatCard.tsx.md`](per-file/apps/web/src/components/common/StatCard.tsx.md) | IMPLEMENTED |
| `apps/web/src/components/common/StatusBadge.tsx` | Frontend | Status display | [`per-file/apps/web/src/components/common/StatusBadge.tsx.md`](per-file/apps/web/src/components/common/StatusBadge.tsx.md) | IMPLEMENTED |
| `apps/web/src/components/common/DataTable.tsx` | Frontend | Reusable accessible table | [`per-file/apps/web/src/components/common/DataTable.tsx.md`](per-file/apps/web/src/components/common/DataTable.tsx.md) | IMPLEMENTED |
| `apps/web/src/components/common/EmptyState.tsx` | Frontend | Empty state | [`per-file/apps/web/src/components/common/EmptyState.tsx.md`](per-file/apps/web/src/components/common/EmptyState.tsx.md) | IMPLEMENTED |
| `apps/web/src/components/common/ErrorState.tsx` | Frontend | Error state | [`per-file/apps/web/src/components/common/ErrorState.tsx.md`](per-file/apps/web/src/components/common/ErrorState.tsx.md) | IMPLEMENTED |
| `apps/web/src/components/common/ConfirmDialog.tsx` | Frontend | Confirmation dialog | [`per-file/apps/web/src/components/common/ConfirmDialog.tsx.md`](per-file/apps/web/src/components/common/ConfirmDialog.tsx.md) | IMPLEMENTED |
| `apps/web/src/components/common/FormField.tsx` | Frontend | Form field wrapper | [`per-file/apps/web/src/components/common/FormField.tsx.md`](per-file/apps/web/src/components/common/FormField.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/auth/LoginPage.tsx` | Frontend | Login page | [`per-file/apps/web/src/features/auth/LoginPage.tsx.md`](per-file/apps/web/src/features/auth/LoginPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/admin/dashboard/AdminDashboardPage.tsx` | Frontend | Admin overview | [`per-file/apps/web/src/features/admin/dashboard/AdminDashboardPage.tsx.md`](per-file/apps/web/src/features/admin/dashboard/AdminDashboardPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/admin/map/DistributionMapPage.tsx` | Frontend | Distribution map | [`per-file/apps/web/src/features/admin/map/DistributionMapPage.tsx.md`](per-file/apps/web/src/features/admin/map/DistributionMapPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/admin/distributors/DistributorsPage.tsx` | Frontend | Distributor management | [`per-file/apps/web/src/features/admin/distributors/DistributorsPage.tsx.md`](per-file/apps/web/src/features/admin/distributors/DistributorsPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/admin/sites/SitesPage.tsx` | Frontend | Site management | [`per-file/apps/web/src/features/admin/sites/SitesPage.tsx.md`](per-file/apps/web/src/features/admin/sites/SitesPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/admin/inventory/InventoryPage.tsx` | Frontend | Inventory and ledger UI | [`per-file/apps/web/src/features/admin/inventory/InventoryPage.tsx.md`](per-file/apps/web/src/features/admin/inventory/InventoryPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/admin/evidence/EvidenceReviewPage.tsx` | Frontend | Evidence review UI | [`per-file/apps/web/src/features/admin/evidence/EvidenceReviewPage.tsx.md`](per-file/apps/web/src/features/admin/evidence/EvidenceReviewPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/admin/analytics/AnalyticsPage.tsx` | Frontend | Analytics and exports | [`per-file/apps/web/src/features/admin/analytics/AnalyticsPage.tsx.md`](per-file/apps/web/src/features/admin/analytics/AnalyticsPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/admin/settings/SettingsPage.tsx` | Frontend | Settings and audit UI | [`per-file/apps/web/src/features/admin/settings/SettingsPage.tsx.md`](per-file/apps/web/src/features/admin/settings/SettingsPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/distributor/dashboard/DistributorDashboardPage.tsx` | Frontend | Distributor home | [`per-file/apps/web/src/features/distributor/dashboard/DistributorDashboardPage.tsx.md`](per-file/apps/web/src/features/distributor/dashboard/DistributorDashboardPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/distributor/sites/AssignedSitesPage.tsx` | Frontend | Assigned sites list | [`per-file/apps/web/src/features/distributor/sites/AssignedSitesPage.tsx.md`](per-file/apps/web/src/features/distributor/sites/AssignedSitesPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/distributor/sites/SiteDetailPage.tsx` | Frontend | Assigned site detail | [`per-file/apps/web/src/features/distributor/sites/SiteDetailPage.tsx.md`](per-file/apps/web/src/features/distributor/sites/SiteDetailPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/distributor/deliveries/DeliverySubmissionPage.tsx` | Frontend | Delivery form workflow | [`per-file/apps/web/src/features/distributor/deliveries/DeliverySubmissionPage.tsx.md`](per-file/apps/web/src/features/distributor/deliveries/DeliverySubmissionPage.tsx.md) | TESTED |
| `apps/web/src/features/distributor/evidence/PhotoCapturePanel.tsx` | Frontend | Photo capture UI | [`per-file/apps/web/src/features/distributor/evidence/PhotoCapturePanel.tsx.md`](per-file/apps/web/src/features/distributor/evidence/PhotoCapturePanel.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/distributor/evidence/useDeviceLocation.ts` | Frontend | Geolocation hook | [`per-file/apps/web/src/features/distributor/evidence/useDeviceLocation.ts.md`](per-file/apps/web/src/features/distributor/evidence/useDeviceLocation.ts.md) | IMPLEMENTED |
| `apps/web/src/features/distributor/offline/offlineQueue.ts` | Frontend | Offline draft queue | [`per-file/apps/web/src/features/distributor/offline/offlineQueue.ts.md`](per-file/apps/web/src/features/distributor/offline/offlineQueue.ts.md) | TESTED |
| `apps/web/src/styles/tokens.css` | Frontend | Design tokens | [`per-file/apps/web/src/styles/tokens.css.md`](per-file/apps/web/src/styles/tokens.css.md) | IMPLEMENTED |
| `apps/web/src/styles/global.css` | Frontend | Global styles | [`per-file/apps/web/src/styles/global.css.md`](per-file/apps/web/src/styles/global.css.md) | IMPLEMENTED |
| `apps/web/vite.config.ts` | DevOps/Lead | Vite config | [`per-file/apps/web/vite.config.ts.md`](per-file/apps/web/vite.config.ts.md) | TESTED |
| `apps/web/package.json` | DevOps/Lead | Web scripts/dependencies | [`per-file/apps/web/package.json.md`](per-file/apps/web/package.json.md) | TESTED |
| `apps/web/Dockerfile` | DevOps/Lead | Web container | [`per-file/apps/web/Dockerfile.md`](per-file/apps/web/Dockerfile.md) | IMPLEMENTED |
| `apps/api/pyproject.toml` | Backend | Python project config | [`per-file/apps/api/pyproject.toml.md`](per-file/apps/api/pyproject.toml.md) | TESTED |
| `apps/api/Dockerfile` | Backend | API container | [`per-file/apps/api/Dockerfile.md`](per-file/apps/api/Dockerfile.md) | IMPLEMENTED |
| `docker-compose.yml` | DevOps/Lead | Local stack | [`per-file/docker-compose.yml.md`](per-file/docker-compose.yml.md) | IMPLEMENTED |
| `.env.example` | DevOps/Lead | Configuration template | [`per-file/.env.example.md`](per-file/.env.example.md) | IMPLEMENTED |
| `Makefile` | DevOps/Lead | Developer commands | [`per-file/Makefile.md`](per-file/Makefile.md) | TESTED |
| `README.md` | DevOps/Lead | Repository run guide | [`per-file/README.md.md`](per-file/README.md.md) | IMPLEMENTED |
| `apps/api/app/models/organization_settings.py` | Backend | Organization settings model | [`per-file/apps/api/app/models/organization_settings.py.md`](per-file/apps/api/app/models/organization_settings.py.md) | TESTED |
| `apps/api/app/schemas/settings.py` | Backend | Settings schemas | [`per-file/apps/api/app/schemas/settings.py.md`](per-file/apps/api/app/schemas/settings.py.md) | TESTED |
| `apps/api/app/schemas/assignments.py` | Backend | Assignment schemas | [`per-file/apps/api/app/schemas/assignments.py.md`](per-file/apps/api/app/schemas/assignments.py.md) | TESTED |
| `apps/api/app/schemas/audit.py` | Backend | Audit schemas | [`per-file/apps/api/app/schemas/audit.py.md`](per-file/apps/api/app/schemas/audit.py.md) | TESTED |
| `apps/api/app/services/campaign_service.py` | Backend | Campaign domain service | [`per-file/apps/api/app/services/campaign_service.py.md`](per-file/apps/api/app/services/campaign_service.py.md) | TESTED |
| `apps/api/app/services/site_service.py` | Backend | Site domain service | [`per-file/apps/api/app/services/site_service.py.md`](per-file/apps/api/app/services/site_service.py.md) | TESTED |
| `apps/api/app/services/assignment_service.py` | Backend | Assignment domain service | [`per-file/apps/api/app/services/assignment_service.py.md`](per-file/apps/api/app/services/assignment_service.py.md) | TESTED |
| `apps/api/app/services/settings_service.py` | Backend | Organization settings service | [`per-file/apps/api/app/services/settings_service.py.md`](per-file/apps/api/app/services/settings_service.py.md) | TESTED |
| `apps/api/app/api/routes/assignments.py` | Backend | Assignment endpoints | [`per-file/apps/api/app/api/routes/assignments.py.md`](per-file/apps/api/app/api/routes/assignments.py.md) | TESTED |
| `apps/api/app/api/routes/settings.py` | Backend | Settings endpoints | [`per-file/apps/api/app/api/routes/settings.py.md`](per-file/apps/api/app/api/routes/settings.py.md) | TESTED |
| `apps/api/app/api/routes/audit.py` | Backend | Audit endpoints | [`per-file/apps/api/app/api/routes/audit.py.md`](per-file/apps/api/app/api/routes/audit.py.md) | TESTED |
| `apps/api/app/cli/create_admin.py` | Backend | First-admin CLI | [`per-file/apps/api/app/cli/create_admin.py.md`](per-file/apps/api/app/cli/create_admin.py.md) | TESTED |
| `apps/api/alembic.ini` | Backend | Alembic configuration | [`per-file/apps/api/alembic.ini.md`](per-file/apps/api/alembic.ini.md) | TESTED |
| `apps/web/index.html` | DevOps/Lead | Web HTML shell | [`per-file/apps/web/index.html.md`](per-file/apps/web/index.html.md) | IMPLEMENTED |
| `apps/web/tsconfig.json` | DevOps/Lead | TypeScript config | [`per-file/apps/web/tsconfig.json.md`](per-file/apps/web/tsconfig.json.md) | TESTED |
| `apps/web/src/features/admin/campaigns/CampaignsPage.tsx` | Frontend | Campaigns and targets UI | [`per-file/apps/web/src/features/admin/campaigns/CampaignsPage.tsx.md`](per-file/apps/web/src/features/admin/campaigns/CampaignsPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/admin/audit/AuditTrailPage.tsx` | Frontend | Audit trail UI | [`per-file/apps/web/src/features/admin/audit/AuditTrailPage.tsx.md`](per-file/apps/web/src/features/admin/audit/AuditTrailPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/distributor/deliveries/MySubmissionsPage.tsx` | Frontend | Distributor submission history | [`per-file/apps/web/src/features/distributor/deliveries/MySubmissionsPage.tsx.md`](per-file/apps/web/src/features/distributor/deliveries/MySubmissionsPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/features/auth/PasswordResetPage.tsx` | Frontend | Password reset UI | [`per-file/apps/web/src/features/auth/PasswordResetPage.tsx.md`](per-file/apps/web/src/features/auth/PasswordResetPage.tsx.md) | IMPLEMENTED |
| `apps/web/src/lib/permissions.test.ts` | Frontend | Permission helper tests | [`per-file/apps/web/src/lib/permissions.test.ts.md`](per-file/apps/web/src/lib/permissions.test.ts.md) | TESTED |
| `apps/web/src/features/distributor/deliveries/DeliverySubmissionPage.test.tsx` | Frontend | Delivery workflow tests | [`per-file/apps/web/src/features/distributor/deliveries/DeliverySubmissionPage.test.tsx.md`](per-file/apps/web/src/features/distributor/deliveries/DeliverySubmissionPage.test.tsx.md) | TESTED |

## Files added during implementation

These files were not in the original plan. Each has a handoff note under `handoffs/per-file/`.

| Target file | Owner | Responsibility | Handoff note | Status |
|---|---|---|---|---|
| `apps/api/app/core/errors.py` | Backend | Shared application errors | [`per-file/apps/api/app/core/errors.py.md`](per-file/apps/api/app/core/errors.py.md) | TESTED |
| `apps/api/app/core/rate_limit.py` | Backend | Auth rate limiting | [`per-file/apps/api/app/core/rate_limit.py.md`](per-file/apps/api/app/core/rate_limit.py.md) | TESTED |
| `apps/api/app/core/units.py` | Backend | Quantity conversion | [`per-file/apps/api/app/core/units.py.md`](per-file/apps/api/app/core/units.py.md) | TESTED |
| `apps/api/app/models/enums.py` | Backend | Shared enums | [`per-file/apps/api/app/models/enums.py.md`](per-file/apps/api/app/models/enums.py.md) | TESTED |
| `apps/api/app/schemas/analytics.py` | Backend | Analytics schemas | [`per-file/apps/api/app/schemas/analytics.py.md`](per-file/apps/api/app/schemas/analytics.py.md) | TESTED |
| `apps/api/app/schemas/common.py` | Backend | Shared schema helpers | [`per-file/apps/api/app/schemas/common.py.md`](per-file/apps/api/app/schemas/common.py.md) | TESTED |
| `apps/api/tests/conftest.py` | Backend | Test harness | [`per-file/apps/api/tests/conftest.py.md`](per-file/apps/api/tests/conftest.py.md) | TESTED |
| `apps/api/requirements.txt` | Backend | Runtime dependency pins | [`per-file/apps/api/requirements.txt.md`](per-file/apps/api/requirements.txt.md) | TESTED |
| `apps/api/requirements-dev.txt` | Backend | Development dependency pins | [`per-file/apps/api/requirements-dev.txt.md`](per-file/apps/api/requirements-dev.txt.md) | TESTED |
| `apps/api/.dockerignore` | DevOps/Lead | API build context filter | [`per-file/apps/api/.dockerignore.md`](per-file/apps/api/.dockerignore.md) | IMPLEMENTED |
| `apps/web/src/lib/format.ts` | Frontend | Shared formatting helpers | [`per-file/apps/web/src/lib/format.ts.md`](per-file/apps/web/src/lib/format.ts.md) | IMPLEMENTED |
| `apps/web/src/features/admin/shared/flags.tsx` | Frontend | Shared geo flags UI | [`per-file/apps/web/src/features/admin/shared/flags.tsx.md`](per-file/apps/web/src/features/admin/shared/flags.tsx.md) | IMPLEMENTED |
| `apps/web/src/lib/api-client.test.ts` | Frontend | API client tests | [`per-file/apps/web/src/lib/api-client.test.ts.md`](per-file/apps/web/src/lib/api-client.test.ts.md) | TESTED |
| `apps/web/vitest.setup.ts` | Frontend | Vitest setup | [`per-file/apps/web/vitest.setup.ts.md`](per-file/apps/web/vitest.setup.ts.md) | TESTED |
| `apps/web/eslint.config.js` | DevOps/Lead | ESLint flat config | [`per-file/apps/web/eslint.config.js.md`](per-file/apps/web/eslint.config.js.md) | TESTED |
| `apps/web/nginx.conf` | DevOps/Lead | Web container server | [`per-file/apps/web/nginx.conf.md`](per-file/apps/web/nginx.conf.md) | IMPLEMENTED |
| `apps/web/.dockerignore` | DevOps/Lead | Web build context filter | [`per-file/apps/web/.dockerignore.md`](per-file/apps/web/.dockerignore.md) | IMPLEMENTED |
| `apps/web/package-lock.json` | DevOps/Lead | Reproducible npm lockfile | [`per-file/apps/web/package-lock.json.md`](per-file/apps/web/package-lock.json.md) | TESTED |
| `apps/api/tests/test_config_security.py` | Backend | Config fail-fast tests | [`per-file/apps/api/tests/test_config_security.py.md`](per-file/apps/api/tests/test_config_security.py.md) | TESTED |
| `apps/web/playwright.config.ts` | QA/Frontend | Browser E2E orchestration | [`per-file/apps/web/playwright.config.ts.md`](per-file/apps/web/playwright.config.ts.md) | TESTED |
| `apps/web/e2e/global-setup.ts` | QA | E2E database/bootstrap lifecycle | [`per-file/apps/web/e2e/global-setup.ts.md`](per-file/apps/web/e2e/global-setup.ts.md) | TESTED |
| `apps/web/e2e/setup.spec.ts` | QA/Backend | E2E data seeding via public APIs | [`per-file/apps/web/e2e/setup.spec.ts.md`](per-file/apps/web/e2e/setup.spec.ts.md) | TESTED |
| `apps/web/e2e/distribution.spec.ts` | QA/Frontend | Critical distributor/reviewer browser flow | [`per-file/apps/web/e2e/distribution.spec.ts.md`](per-file/apps/web/e2e/distribution.spec.ts.md) | TESTED |
| `apps/web/e2e/support/config.ts` | QA | Shared E2E identifiers/fixtures | [`per-file/apps/web/e2e/support/config.ts.md`](per-file/apps/web/e2e/support/config.ts.md) | TESTED |
| `apps/web/e2e/support/credentials.ts` | QA | Per-run E2E credential reader | [`per-file/apps/web/e2e/support/credentials.ts.md`](per-file/apps/web/e2e/support/credentials.ts.md) | TESTED |
| `apps/web/e2e/support/prepare_db.py` | QA | Disposable E2E database creation | [`per-file/apps/web/e2e/support/prepare_db.py.md`](per-file/apps/web/e2e/support/prepare_db.py.md) | TESTED |
