"""Administrator distributor account endpoints."""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..auth import IsAdminRole
from ..models import DistributorAssignment, Invitation, StockAccount, User
from ..presenters import distributor_out, page
from ..serializers import DistributorUpdateSerializer
from ..services import auth as auth_service
from ..services import inventory as inventory_service
from ..services.audit import record_audit
from .helpers import get_distributor_or_404, pagination, response_ctx


def _detail_payload(user: User, *, with_counts: bool = True) -> dict:
    account = StockAccount.objects.filter(owner_user_id=user.id).first()
    balance = inventory_service.posted_balance_kg(account.id) if account else Decimal("0")
    reserved = inventory_service.reserved_kg(user.id)
    payload = {
        **distributor_out(user),
        "stock_balance_kg": str(balance),
        "reserved_kg": str(reserved),
        "available_kg": str(balance - reserved),
    }
    if with_counts:
        payload["assigned_campaign_count"] = (
            DistributorAssignment.objects.filter(distributor_user_id=user.id)
            .exclude(campaign__isnull=True)
            .values("campaign_id")
            .distinct()
            .count()
        )
        payload["open_assignment_count"] = DistributorAssignment.objects.filter(
            distributor_user_id=user.id, status__in=["ACTIVE", "PAUSED"]
        ).count()
        payload["has_open_invitation"] = Invitation.objects.filter(
            email=user.email,
            accepted_at__isnull=True,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).exists()
    return payload


@api_view(["GET"])
@permission_classes([IsAdminRole])
def list_distributors(request):
    limit, offset = pagination(request)
    query = User.objects.filter(role="DISTRIBUTOR")
    search = request.query_params.get("search")
    if search:
        query = query.filter(Q(display_name__icontains=search) | Q(email__icontains=search))
    total = query.count()
    users = query.order_by("-created_at")[offset : offset + limit]
    return Response(page([_detail_payload(user) for user in users], total, limit, offset))


def _get_distributor(request, user_id: uuid.UUID):
    return Response(_detail_payload(get_distributor_or_404(user_id)))


def _update_distributor(request, user_id: uuid.UUID):
    target = get_distributor_or_404(user_id)
    serializer = DistributorUpdateSerializer(data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    with transaction.atomic():
        if "display_name" in data:
            target.display_name = data["display_name"]
            target.save(update_fields=["display_name", "updated_at"])
        record_audit(
            actor=request.user,
            action="user.updated",
            target_type="user",
            target_id=target.id,
            details={"changed_fields": list(data.keys())},
            ctx=response_ctx(request),
        )
    return Response(_detail_payload(target))


@api_view(["GET", "PATCH"])
@permission_classes([IsAdminRole])
def distributor_detail(request, user_id: uuid.UUID):
    if request.method == "PATCH":
        return _update_distributor(request, user_id)
    return _get_distributor(request, user_id)


@api_view(["POST"])
@permission_classes([IsAdminRole])
def deactivate_distributor(request, user_id: uuid.UUID):
    target = get_distributor_or_404(user_id)
    with transaction.atomic():
        auth_service.deactivate_user(admin=request.user, target=target, ctx=response_ctx(request))
    target.refresh_from_db()
    return Response(distributor_out(target))
