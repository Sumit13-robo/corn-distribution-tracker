"""Analytics and CSV export endpoints."""

from __future__ import annotations

import csv
import io

from django.db import transaction
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from ..auth import IsAdminRole
from ..enums import RecordStatus
from ..errors import AppError
from ..models import DistributionSite, User
from ..services import analytics as analytics_service
from ..services import distribution as distribution_service
from ..services.audit import record_audit
from .helpers import (
    json_response,
    parse_bbox,
    query_datetime,
    query_uuid,
    response_ctx,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def overview(request):
    scope_user = None if request.user.role == "ADMIN" else request.user
    data = analytics_service.overview(
        scope_user=scope_user,
        campaign_id=query_uuid(request, "campaign_id"),
        from_ts=query_datetime(request, "from"),
        to_ts=query_datetime(request, "to"),
    )
    return json_response(data)


@api_view(["GET"])
@permission_classes([IsAdminRole])
def distributor_analytics(request):
    rows = analytics_service.distributor_performance(
        campaign_id=query_uuid(request, "campaign_id"),
        from_ts=query_datetime(request, "from"),
        to_ts=query_datetime(request, "to"),
    )
    return json_response(rows)


@api_view(["GET"])
@permission_classes([IsAdminRole])
def site_analytics(request):
    rows = analytics_service.site_performance(
        campaign_id=query_uuid(request, "campaign_id"),
        from_ts=query_datetime(request, "from"),
        to_ts=query_datetime(request, "to"),
    )
    return json_response(rows)


@api_view(["GET"])
@permission_classes([IsAdminRole])
def map_sites(request):
    bbox = parse_bbox(request.query_params.get("bbox"))
    rows = analytics_service.map_sites(
        bbox=bbox,
        campaign_id=query_uuid(request, "campaign_id"),
        distributor_user_id=query_uuid(request, "distributor_user_id"),
    )
    return json_response(rows)


def _safe_cell(value: str) -> str:
    if value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


@api_view(["GET"])
@permission_classes([IsAdminRole])
def export_distributions_csv(request):
    status = request.query_params.get("status")
    if status:
        try:
            RecordStatus(status)
        except ValueError:
            raise AppError("Unknown record status.", details=[{"field": "status"}]) from None
    query = distribution_service.scope_records_query(
        user=request.user,
        status=status,
        campaign_id=query_uuid(request, "campaign_id"),
        site_id=None,
        distributor_user_id=query_uuid(request, "distributor_user_id"),
        from_ts=query_datetime(request, "from"),
        to_ts=query_datetime(request, "to"),
    )
    records = list(query.order_by("-submitted_at")[:10_000])
    sites = {site.id: site for site in DistributionSite.objects.all()}
    distributors = {user.id: user for user in User.objects.filter(role="DISTRIBUTOR")}

    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(
        [
            "record_id",
            "submitted_at",
            "status",
            "site_code",
            "site_name",
            "distributor_email",
            "quantity_kg",
            "geo_status",
            "geo_flags",
            "review_reason",
            "stock_movement_id",
        ]
    )
    for record in records:
        site = sites.get(record.site_id)
        distributor = distributors.get(record.distributor_user_id)
        writer.writerow(
            [
                _safe_cell(str(record.id)),
                (record.submitted_at.isoformat().replace("+00:00", "Z") if record.submitted_at else ""),
                record.status,
                _safe_cell(site.site_code if site else ""),
                _safe_cell(site.name if site else ""),
                _safe_cell(distributor.email if distributor else ""),
                str(record.quantity_kg),
                record.geo_status,
                _safe_cell(",".join(record.geo_flags or [])),
                _safe_cell(record.review_reason or ""),
                str(record.stock_movement_id or ""),
            ]
        )
    with transaction.atomic():
        record_audit(
            actor=request.user,
            action="export.distributions",
            target_type="distribution_record",
            details={
                "count": len(records),
                "filters": {
                    "campaign_id": request.query_params.get("campaign_id"),
                    "status": status,
                    "distributor_user_id": request.query_params.get("distributor_user_id"),
                },
            },
            ctx=response_ctx(request),
        )
    response = HttpResponse(buffer.getvalue().encode("utf-8"), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        "attachment; filename=\"distributions.csv\"; filename*=UTF-8''distributions.csv"
    )
    return response
