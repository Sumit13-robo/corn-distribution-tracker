"""Delivery submission and review endpoints."""

from __future__ import annotations

import uuid

from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from ..auth import IsAdminRole
from ..enums import RecordStatus
from ..errors import AppError
from ..presenters import page
from ..serializers import (
    ApprovalSerializer,
    CancelSerializer,
    DeliveryCreateSerializer,
    RejectSerializer,
)
from ..services import distribution as distribution_service
from .helpers import (
    detail_record,
    json_response,
    pagination,
    query_datetime,
    query_uuid,
    response_ctx,
)


def _delivery_key(request) -> str:
    raw = request.headers.get("Idempotency-Key", "").strip()
    return (raw or f"delivery:{uuid.uuid4()}")[:64]


def _submit_delivery(request):
    serializer = DeliveryCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    with transaction.atomic():
        record, _duplicate = distribution_service.submit_delivery(
            user=request.user,
            assignment_id=data["assignment_id"],
            quantity=data["quantity"],
            unit=data["unit"],
            notes=data.get("notes"),
            evidence_specs=data["evidence"],
            location=data.get("location"),
            idempotency_key=_delivery_key(request),
            ctx=response_ctx(request),
        )
    return json_response(detail_record(record), status=201)


def _list_deliveries(request):
    limit, offset = pagination(request)
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
        site_id=query_uuid(request, "site_id"),
        distributor_user_id=query_uuid(request, "distributor_user_id"),
        from_ts=query_datetime(request, "from"),
        to_ts=query_datetime(request, "to"),
    )
    total = query.count()
    rows = query.order_by("-submitted_at")[offset : offset + limit]
    return json_response(page([detail_record(record) for record in rows], total, limit, offset))


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def deliveries_collection(request):
    if request.method == "POST":
        return _submit_delivery(request)
    return _list_deliveries(request)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_delivery(request, record_id: uuid.UUID):
    record = distribution_service.get_record_scoped(user=request.user, record_id=record_id)
    return json_response(detail_record(record))


@api_view(["POST"])
@permission_classes([IsAdminRole])
def approve_delivery(request, record_id: uuid.UUID):
    serializer = ApprovalSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    with transaction.atomic():
        record, _duplicate = distribution_service.approve_delivery(
            admin=request.user,
            record_id=record_id,
            exception_reason=data.get("exception_reason"),
            review_note=data.get("review_note"),
            idempotency_key=request.headers.get("Idempotency-Key") or None,
            ctx=response_ctx(request),
        )
    return json_response(detail_record(record))


@api_view(["POST"])
@permission_classes([IsAdminRole])
def reject_delivery(request, record_id: uuid.UUID):
    serializer = RejectSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        record, _duplicate = distribution_service.reject_delivery(
            admin=request.user,
            record_id=record_id,
            reason=serializer.validated_data["reason"],
            ctx=response_ctx(request),
        )
    return json_response(detail_record(record))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_delivery(request, record_id: uuid.UUID):
    serializer = CancelSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        record, _duplicate = distribution_service.cancel_delivery(
            actor=request.user,
            record_id=record_id,
            reason=serializer.validated_data.get("reason"),
            ctx=response_ctx(request),
        )
    return json_response(detail_record(record))
