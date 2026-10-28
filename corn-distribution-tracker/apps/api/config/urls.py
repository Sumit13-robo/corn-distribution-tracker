"""Root URL configuration. All application endpoints live under /api/v1."""

from __future__ import annotations

from django.conf import settings
from django.urls import path

from corn.errors import json_404, json_500
from corn.views import (
    analytics as analytics_views,
)
from corn.views import (
    assignments as assignment_views,
)
from corn.views import (
    auth as auth_views,
)
from corn.views import (
    campaigns as campaign_views,
)
from corn.views import (
    deliveries as delivery_views,
)
from corn.views import (
    evidence as evidence_views,
)
from corn.views import (
    health as health_views,
)
from corn.views import (
    inventory as inventory_views,
)
from corn.views import (
    settings as settings_views,
)
from corn.views import (
    sites as site_views,
)
from corn.views import (
    users as user_views,
)

API = settings.API_V1_PREFIX.strip("/")

urlpatterns = [
    path("health/live", health_views.live),
    path("health/ready", health_views.ready),
    path(f"{API}/health/live", health_views.live),
    path(f"{API}/health/ready", health_views.ready),
    # Auth and account lifecycle
    path(f"{API}/auth/login", auth_views.login),
    path(f"{API}/auth/me", auth_views.me),
    path(f"{API}/auth/csrf", auth_views.csrf),
    path(f"{API}/auth/logout", auth_views.logout),
    path(f"{API}/auth/change-password", auth_views.change_password),
    path(f"{API}/auth/forgot-password", auth_views.forgot_password),
    path(f"{API}/auth/reset-password", auth_views.reset_password),
    path(f"{API}/auth/accept-invitation", auth_views.accept_invitation),
    path(f"{API}/admin/users/invitations", auth_views.invitations_collection),
    # Distributors
    path(f"{API}/admin/distributors", user_views.list_distributors),
    path(f"{API}/admin/distributors/<uuid:user_id>", user_views.distributor_detail),
    path(f"{API}/admin/distributors/<uuid:user_id>/deactivate", user_views.deactivate_distributor),
    path(f"{API}/distributors/me/assignments", assignment_views.my_assignments),
    # Campaigns
    path(f"{API}/campaigns", campaign_views.campaigns_collection),
    path(f"{API}/campaigns/<uuid:campaign_id>", campaign_views.campaign_detail),
    # Sites
    path(f"{API}/sites", site_views.sites_collection),
    path(f"{API}/sites/<uuid:site_id>", site_views.site_detail),
    path(f"{API}/sites/<uuid:site_id>/progress", site_views.site_progress),
    path(f"{API}/sites/<uuid:site_id>/deactivate", site_views.deactivate_site),
    # Assignments
    path(f"{API}/assignments", assignment_views.assignments_collection),
    path(f"{API}/assignments/<uuid:assignment_id>", assignment_views.assignment_detail),
    # Inventory
    path(f"{API}/inventory/summary", inventory_views.summary),
    path(f"{API}/inventory/accounts/<uuid:account_id>/ledger", inventory_views.account_ledger),
    path(f"{API}/inventory/receipts", inventory_views.receive_stock),
    path(f"{API}/inventory/allocations", inventory_views.allocate_stock),
    path(f"{API}/inventory/adjustments", inventory_views.adjust_stock),
    path(f"{API}/inventory/movements/<uuid:movement_id>/reversal", inventory_views.reverse_movement),
    path(f"{API}/inventory/display-unit", inventory_views.display_unit),
    # Deliveries
    path(f"{API}/deliveries", delivery_views.deliveries_collection),
    path(f"{API}/deliveries/<uuid:record_id>", delivery_views.get_delivery),
    path(f"{API}/deliveries/<uuid:record_id>/approve", delivery_views.approve_delivery),
    path(f"{API}/deliveries/<uuid:record_id>/reject", delivery_views.reject_delivery),
    path(f"{API}/deliveries/<uuid:record_id>/cancel", delivery_views.cancel_delivery),
    # Evidence
    path(f"{API}/evidence/upload-intents", evidence_views.create_upload_intent),
    path(
        f"{API}/evidence/upload-intents/<uuid:intent_id>/complete",
        evidence_views.complete_upload_intent,
    ),
    path(f"{API}/evidence/objects/<uuid:intent_id>", evidence_views.put_object),
    path(f"{API}/evidence/<uuid:evidence_id>/view-url", evidence_views.view_url),
    path(f"{API}/evidence/blob/<uuid:evidence_id>", evidence_views.blob),
    # Analytics and export
    path(f"{API}/analytics/overview", analytics_views.overview),
    path(f"{API}/analytics/distributors", analytics_views.distributor_analytics),
    path(f"{API}/analytics/sites", analytics_views.site_analytics),
    path(f"{API}/analytics/map-deliveries", analytics_views.map_deliveries),
    path(f"{API}/analytics/map-sites", analytics_views.map_sites),
    path(f"{API}/exports/distributions.csv", analytics_views.export_distributions_csv),
    # Settings and audit
    path(f"{API}/settings", settings_views.settings_detail),
    path(f"{API}/audit/events", settings_views.audit_events),
]

handler404 = json_404
handler500 = json_500
