"""Organization settings and append-only audit trail endpoints."""

from __future__ import annotations

import zoneinfo

from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from ..auth import IsAdminRole
from ..errors import AppError
from ..presenters import audit_event_out, page, settings_out
from ..serializers import SettingsPatchSerializer
from ..services import audit as audit_service
from ..services import settings as settings_service
from .helpers import (
    json_response,
    pagination,
    query_datetime,
    query_uuid,
    require_admin,
    response_ctx,
)


def _get_settings(request):
    return json_response(settings_out(settings_service.get_or_create_settings()))


def _patch_settings(request):
    serializer = SettingsPatchSerializer(data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    data = dict(serializer.validated_data)
    if "timezone" in data:
        try:
            zoneinfo.ZoneInfo(data["timezone"])
        except Exception:
            raise AppError("Unknown timezone.", details=[{"field": "timezone"}]) from None
    with transaction.atomic():
        row = settings_service.update_settings(
            admin=request.user, payload=data, ctx=response_ctx(request)
        )
    return json_response(settings_out(row))


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def settings_detail(request):
    if request.method == "PATCH":
        require_admin(request)
        return _patch_settings(request)
    return _get_settings(request)


@api_view(["GET"])
@permission_classes([IsAdminRole])
def audit_events(request):
    limit, offset = pagination(request)
    rows, total = audit_service.list_audit_events(
        action=request.query_params.get("action"),
        actor_user_id=query_uuid(request, "actor_user_id"),
        target_type=request.query_params.get("target_type"),
        target_id=query_uuid(request, "target_id"),
        occurred_from=query_datetime(request, "from"),
        occurred_to=query_datetime(request, "to"),
        limit=limit,
        offset=offset,
    )
    return json_response(page([audit_event_out(row) for row in rows], total, limit, offset))
