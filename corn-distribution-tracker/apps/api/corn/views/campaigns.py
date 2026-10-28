"""Campaign endpoints. DRF views dispatch GET/POST (and GET/PATCH) explicitly."""

from __future__ import annotations

import uuid

from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..enums import CampaignStatus
from ..errors import AppError
from ..presenters import campaign_out, page
from ..serializers import CampaignCreateSerializer, CampaignPatchSerializer
from ..services import campaigns as campaign_service
from .helpers import pagination, require_admin, response_ctx


def _list_campaigns(request):
    limit, offset = pagination(request)
    status = request.query_params.get("status")
    if status:
        try:
            CampaignStatus(status)
        except ValueError:
            raise AppError("Unknown campaign status.", details=[{"field": "status"}]) from None
    rows, total = campaign_service.list_campaigns(
        viewer=request.user, status=status, limit=limit, offset=offset
    )
    include_notes = request.user.role == "ADMIN"
    return Response(
        page([campaign_out(row, include_notes=include_notes) for row in rows], total, limit, offset)
    )


def _create_campaign(request):
    serializer = CampaignCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        campaign = campaign_service.create_campaign(
            admin=request.user, data=serializer.validated_data, ctx=response_ctx(request)
        )
    return Response(campaign_out(campaign), status=201)


def _get_campaign(request, campaign_id: uuid.UUID):
    campaign = campaign_service.get_campaign(viewer=request.user, campaign_id=campaign_id)
    include_notes = request.user.role == "ADMIN"
    return Response(campaign_out(campaign, include_notes=include_notes))


def _update_campaign(request, campaign_id: uuid.UUID):
    serializer = CampaignPatchSerializer(data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        campaign = campaign_service.update_campaign(
            admin=request.user,
            campaign_id=campaign_id,
            data=serializer.validated_data,
            ctx=response_ctx(request),
        )
    return Response(campaign_out(campaign))


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def campaigns_collection(request):
    if request.method == "POST":
        require_admin(request)
        return _create_campaign(request)
    return _list_campaigns(request)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def campaign_detail(request, campaign_id: uuid.UUID):
    if request.method == "PATCH":
        require_admin(request)
        return _update_campaign(request, campaign_id)
    return _get_campaign(request, campaign_id)
