"""Site endpoints (admin CRUD; distributors see only assigned sites)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..enums import RecordStatus
from ..errors import AppError, NotFoundError
from ..models import DistributionRecord, DistributorAssignment, PhotoEvidence
from ..presenters import page, site_out
from ..serializers import SiteCreateSerializer, SitePatchSerializer
from ..services import campaigns as site_service
from .helpers import pagination, require_admin, response_ctx

ZERO = Decimal("0")
INTEGRITY_FLAGS = {
    "UNEXPECTED_FILE_TYPE",
    "CAPTURE_TIME_MISMATCH",
    "DUPLICATE_IMAGE_HASH",
}


def _parse_bool(raw: str | None, field: str) -> bool | None:
    if raw is None or raw == "":
        return None
    lowered = raw.lower()
    if lowered in {"true", "1"}:
        return True
    if lowered in {"false", "0"}:
        return False
    raise AppError(f"{field} must be true or false.", details=[{"field": field}])


def _assigned_to_site(user, site_id: uuid.UUID) -> bool:
    return DistributorAssignment.objects.filter(
        site_id=site_id, distributor_user_id=user.id
    ).exists()


def _list_sites(request):
    limit, offset = pagination(request)
    search = request.query_params.get("search")
    active_only = _parse_bool(request.query_params.get("active_only"), "active_only") or False
    campaign_id = None
    raw_campaign = request.query_params.get("campaign_id")
    if raw_campaign:
        try:
            campaign_id = uuid.UUID(raw_campaign)
        except ValueError:
            raise AppError("campaign_id must be a UUID.", details=[{"field": "campaign_id"}]) from None
    if request.user.role == "ADMIN":
        rows, total = site_service.list_sites(
            active_only=active_only,
            search=search,
            campaign_id=campaign_id,
            limit=limit,
            offset=offset,
        )
    else:
        rows, total = site_service.assigned_sites(
            user=request.user, search=search, limit=limit, offset=offset
        )
    include_notes = request.user.role == "ADMIN"
    return Response(
        page([site_out(row, include_notes=include_notes) for row in rows], total, limit, offset)
    )


def _create_site(request):
    serializer = SiteCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        site = site_service.create_site(
            admin=request.user, data=serializer.validated_data, ctx=response_ctx(request)
        )
    return Response(site_out(site), status=201)


def _get_site(request, site_id: uuid.UUID):
    site = site_service.get_site(site_id)
    if request.user.role != "ADMIN" and not _assigned_to_site(request.user, site_id):
        raise NotFoundError("Site not found.")
    return Response(site_out(site, include_notes=request.user.role == "ADMIN"))


def _update_site(request, site_id: uuid.UUID):
    serializer = SitePatchSerializer(data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    data = dict(serializer.validated_data)
    for required_field in (
        "name",
        "site_code",
        "geofence_radius_m",
        "is_active",
    ):
        if required_field in data and data[required_field] is None:
            raise AppError(
                f"{required_field} cannot be null.", details=[{"field": required_field}]
            )
    with transaction.atomic():
        site = site_service.update_site(
            admin=request.user, site_id=site_id, data=data, ctx=response_ctx(request)
        )
    return Response(site_out(site))


def _site_progress(request, site_id: uuid.UUID):
    site_service.get_site(site_id)
    if request.user.role != "ADMIN" and not _assigned_to_site(request.user, site_id):
        raise NotFoundError("Site not found.")
    raw_campaign = request.query_params.get("campaign_id")
    campaign_id = None
    if raw_campaign:
        try:
            campaign_id = uuid.UUID(raw_campaign)
        except ValueError:
            raise AppError("campaign_id must be a UUID.", details=[{"field": "campaign_id"}]) from None
    records_query = DistributionRecord.objects.filter(site_id=site_id)
    assignments_query = DistributorAssignment.objects.filter(site_id=site_id)
    if request.user.role != "ADMIN":
        records_query = records_query.filter(distributor_user_id=request.user.id)
        assignments_query = assignments_query.filter(distributor_user_id=request.user.id)
    if campaign_id:
        records_query = records_query.filter(campaign_id=campaign_id)
        assignments_query = assignments_query.filter(campaign_id=campaign_id)
    records = list(records_query)
    target = assignments_query.aggregate(total=Sum("target_quantity_kg"))["total"] or ZERO
    approved = sum(
        (Decimal(record.quantity_kg) for record in records if record.status == RecordStatus.APPROVED),
        ZERO,
    )
    pending = sum(
        (Decimal(record.quantity_kg) for record in records if record.status == RecordStatus.SUBMITTED),
        ZERO,
    )
    rejected = sum(
        (Decimal(record.quantity_kg) for record in records if record.status == RecordStatus.REJECTED),
        ZERO,
    )
    record_ids = [record.id for record in records]
    has_evidence = (
        PhotoEvidence.objects.filter(distribution_record_id__in=record_ids).exists()
        if record_ids
        else False
    )
    evidence_status = (
        "EVIDENCE_PRESENT" if has_evidence else ("NONE" if not records else "EVIDENCE_MISSING")
    )
    last_visit = max((record.submitted_at for record in records), default=None)
    flagged = any(set(record.geo_flags or []) & INTEGRITY_FLAGS for record in records)
    from .helpers import json_response

    return json_response(
        {
            "target_kg": target,
            "submitted_kg": approved + pending + rejected,
            "approved_kg": approved,
            "pending_kg": pending,
            "rejected_kg": rejected,
            "remaining_target_kg": max(Decimal(target) - approved, ZERO),
            "submission_count": len(records),
            "last_visit_at": last_visit,
            "evidence_status": evidence_status,
            "has_flagged_evidence": flagged,
        }
    )


def _deactivate_site(request, site_id: uuid.UUID):
    with transaction.atomic():
        site = site_service.deactivate_site(
            admin=request.user, site_id=site_id, ctx=response_ctx(request)
        )
    return Response(site_out(site))


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def sites_collection(request):
    if request.method == "POST":
        require_admin(request)
        return _create_site(request)
    return _list_sites(request)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def site_detail(request, site_id: uuid.UUID):
    if request.method == "PATCH":
        require_admin(request)
        return _update_site(request, site_id)
    return _get_site(request, site_id)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def site_progress(request, site_id: uuid.UUID):
    return _site_progress(request, site_id)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def deactivate_site(request, site_id: uuid.UUID):
    require_admin(request)
    return _deactivate_site(request, site_id)
