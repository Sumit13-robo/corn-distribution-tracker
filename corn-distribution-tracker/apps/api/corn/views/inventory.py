"""Inventory ledger endpoints: summary, ledger, receipts, allocations and adjustments."""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from ..auth import IsAdminRole
from ..enums import DisplayUnit
from ..errors import AppError, NotFoundError, UnprocessableEntityError
from ..models import StockAccount, StockMovement
from ..presenters import movement_out, page
from ..serializers import (
    AdjustmentSerializer,
    AllocationSerializer,
    ReceiptSerializer,
    ReversalSerializer,
)
from ..services import inventory as inventory_service
from ..services import settings as settings_service
from ..units import kg_to_display, unit_factor_label
from .helpers import json_response, pagination, response_ctx

ZERO = Decimal("0")


def _idempotency(request, prefix: str) -> str:
    raw = request.headers.get("Idempotency-Key", "").strip()
    if len(raw) > 128:
        raise AppError(
            "Idempotency-Key must be 128 characters or fewer.",
            details=[{"field": "Idempotency-Key"}],
        )
    return raw or f"{prefix}:{uuid.uuid4()}"


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def summary(request):
    scope_user = None if request.user.role == "ADMIN" else request.user
    accounts = inventory_service.account_summaries(scope_user=scope_user)
    reconciliation = inventory_service.reconciliation_summary() if request.user.role == "ADMIN" else None
    return json_response(
        {
            "accounts": [
                {
                    "id": account["id"],
                    "account_type": account["account_type"],
                    "name": account["name"],
                    "owner_user_id": account["owner_user_id"],
                    "site_id": account["site_id"],
                    "posted_balance_kg": account["posted_balance_kg"],
                    "reserved_kg": account["reserved_kg"],
                    "available_kg": account["available_kg"],
                }
                for account in accounts
            ],
            "reconciliation": reconciliation,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def account_ledger(request, account_id: uuid.UUID):
    limit, offset = pagination(request)
    account = StockAccount.objects.filter(id=account_id).first()
    if account is None:
        raise NotFoundError("Account not found.")
    if request.user.role != "ADMIN" and account.owner_user_id != request.user.id:
        raise NotFoundError("Account not found.")
    query = StockMovement.objects.filter(
        Q(source_account_id=account_id) | Q(destination_account_id=account_id)
    )
    total = query.count()
    rows = (
        query.select_related("reversal_of", "reversal")
        .order_by("-posted_at", "-id")[offset : offset + limit]
    )
    return json_response(page([movement_out(row) for row in rows], total, limit, offset))


@api_view(["POST"])
@permission_classes([IsAdminRole])
def receive_stock(request):
    serializer = ReceiptSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    with transaction.atomic():
        movement = inventory_service.receive_stock(
            admin=request.user,
            quantity=data["quantity"],
            unit=data["unit"],
            source_reference=data["source_reference"],
            received_at=data.get("received_at"),
            notes=data.get("notes"),
            idempotency_key=_idempotency(request, "receipt"),
            ctx=response_ctx(request),
        )
    return json_response(movement_out(movement), status=201)


@api_view(["POST"])
@permission_classes([IsAdminRole])
def allocate_stock(request):
    serializer = AllocationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    with transaction.atomic():
        movement = inventory_service.allocate_stock(
            admin=request.user,
            distributor_user_id=data["distributor_user_id"],
            quantity=data["quantity"],
            unit=data["unit"],
            campaign_id=data.get("campaign_id"),
            notes=data.get("notes"),
            idempotency_key=_idempotency(request, "allocation"),
            ctx=response_ctx(request),
        )
    return json_response(movement_out(movement), status=201)


@api_view(["POST"])
@permission_classes([IsAdminRole])
def adjust_stock(request):
    serializer = AdjustmentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    with transaction.atomic():
        movement = inventory_service.adjust_stock(
            admin=request.user,
            account_id=data["account_id"],
            quantity=data["quantity"],
            unit=data["unit"],
            movement_type=data["movement_type"],
            reason=data["reason"],
            destination_account_id=data.get("destination_account_id"),
            idempotency_key=_idempotency(request, "adjustment"),
            ctx=response_ctx(request),
        )
    return json_response(movement_out(movement), status=201)


@api_view(["POST"])
@permission_classes([IsAdminRole])
def reverse_movement(request, movement_id: uuid.UUID):
    serializer = ReversalSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        movement = inventory_service.reverse_movement(
            admin=request.user,
            movement_id=movement_id,
            reason=serializer.validated_data["reason"],
            idempotency_key=_idempotency(request, "reversal"),
            ctx=response_ctx(request),
        )
    return json_response(movement_out(movement), status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def display_unit(request):
    raw_quantity = request.query_params.get("quantity_kg")
    if raw_quantity is None:
        raise UnprocessableEntityError(
            "quantity_kg is required.", details=[{"field": "quantity_kg"}]
        )
    try:
        quantity_kg = Decimal(raw_quantity)
    except (InvalidOperation, ValueError):
        raise UnprocessableEntityError(
            "quantity_kg must be a number.", details=[{"field": "quantity_kg"}]
        ) from None
    settings_row = settings_service.get_or_create_settings()
    unit_raw = request.query_params.get("unit") or settings_row.default_display_unit
    try:
        unit = DisplayUnit(unit_raw)
    except ValueError:
        raise UnprocessableEntityError(
            "Unsupported display unit.", details=[{"field": "unit"}]
        ) from None
    display_value = kg_to_display(quantity_kg, unit, settings_row.kg_per_bag)
    return json_response(
        {
            "quantity_kg": quantity_kg,
            "unit": unit.value,
            "factor_label": unit_factor_label(unit, settings_row.kg_per_bag),
            "display_value": display_value,
        }
    )
