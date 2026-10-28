"""Assignment endpoints for administrators and distributor self-service."""

from __future__ import annotations

import uuid

from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..presenters import assignment_out, page
from ..serializers import AssignmentCreateSerializer, AssignmentPatchSerializer
from ..services import campaigns as assignment_service
from .helpers import (
    json_response,
    pagination,
    query_uuid,
    require_admin,
    response_ctx,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_assignments(request):
    return json_response(assignment_service.distributor_me_assignments(user=request.user))


def _list_assignments(request):
    limit, offset = pagination(request)
    campaign_id = query_uuid(request, "campaign_id")
    rows, total = assignment_service.list_assignments(
        user=request.user, campaign_id=campaign_id, limit=limit, offset=offset
    )
    include_notes = request.user.role == "ADMIN"
    return Response(
        page(
            [assignment_out(row, include_notes=include_notes) for row in rows],
            total,
            limit,
            offset,
        )
    )


def _create_assignment(request):
    serializer = AssignmentCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        assignment = assignment_service.create_assignment(
            admin=request.user, data=serializer.validated_data, ctx=response_ctx(request)
        )
    return Response(assignment_out(assignment), status=201)


def _get_assignment(request, assignment_id: uuid.UUID):
    assignment = assignment_service.get_assignment_scoped(
        user=request.user, assignment_id=assignment_id
    )
    return Response(assignment_out(assignment, include_notes=request.user.role == "ADMIN"))


def _update_assignment(request, assignment_id: uuid.UUID):
    serializer = AssignmentPatchSerializer(data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        assignment = assignment_service.update_assignment(
            admin=request.user,
            assignment_id=assignment_id,
            data=serializer.validated_data,
            ctx=response_ctx(request),
        )
    return Response(assignment_out(assignment))


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def assignments_collection(request):
    if request.method == "POST":
        require_admin(request)
        return _create_assignment(request)
    return _list_assignments(request)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def assignment_detail(request, assignment_id: uuid.UUID):
    if request.method == "PATCH":
        require_admin(request)
        return _update_assignment(request, assignment_id)
    return _get_assignment(request, assignment_id)
