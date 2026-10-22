"""Shared view helpers: pagination, UUID/date query parsing and presenters."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.utils.dateparse import parse_datetime
from rest_framework.request import Request

from ..errors import NotFoundError, UnprocessableEntityError
from ..models import DistributionRecord, PhotoEvidence
from ..presenters import distribution_out, jsonable
from ..services.audit import RequestContext, context_from_request


def pagination(request: Request) -> tuple[int, int]:
    try:
        limit = int(request.query_params.get("limit", 25))
        offset = int(request.query_params.get("offset", 0))
    except (TypeError, ValueError):
        raise UnprocessableEntityError(
            "limit and offset must be integers.",
            details=[{"field": "pagination"}],
        ) from None
    if limit < 1 or limit > 100:
        raise UnprocessableEntityError("limit must be between 1 and 100.", details=[{"field": "limit"}])
    if offset < 0:
        raise UnprocessableEntityError("offset must be non-negative.", details=[{"field": "offset"}])
    return limit, offset


def query_uuid(request: Request, name: str) -> uuid.UUID | None:
    raw = request.query_params.get(name)
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except (ValueError, TypeError):
        raise UnprocessableEntityError(f"{name} must be a UUID.", details=[{"field": name}]) from None


def query_datetime(request: Request, name: str) -> datetime | None:
    raw = request.query_params.get(name)
    if not raw:
        return None
    parsed = parse_datetime(raw)
    if parsed is None:
        raise UnprocessableEntityError(f"{name} must be an ISO-8601 datetime.", details=[{"field": name}])
    return parsed


def response_ctx(request: Request) -> RequestContext:
    return context_from_request(request)


def require_admin(request) -> None:
    """Raise DRF's 403 for collection endpoints where POST/PATCH is admin-only."""
    from rest_framework.exceptions import PermissionDenied

    from ..auth import IsAdminRole

    if not IsAdminRole().has_permission(request, None):
        raise PermissionDenied("Administrator role required.")


def detail_record(record: DistributionRecord) -> dict[str, Any]:
    evidence = list(
        PhotoEvidence.objects.filter(distribution_record_id=record.id).order_by(
            "server_received_at"
        )
    )
    return distribution_out(record, evidence)


def json_response(data: Any, status: int = 200):
    from rest_framework.response import Response

    return Response(jsonable(data), status=status)


def movement_payload(movement) -> dict[str, Any]:
    from ..presenters import movement_out

    return movement_out(movement)


def account_payload(account: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": account["id"],
        "account_type": account["account_type"],
        "name": account["name"],
        "owner_user_id": account["owner_user_id"],
        "site_id": account["site_id"],
        "posted_balance_kg": account["posted_balance_kg"],
        "reserved_kg": account["reserved_kg"],
        "available_kg": account["available_kg"],
    }


def get_distributor_or_404(user_id: uuid.UUID):
    from ..models import User

    user = User.objects.filter(id=user_id, role="DISTRIBUTOR").first()
    if user is None:
        raise NotFoundError("Distributor not found.")
    return user


def set_csrf_cookie(request: Request) -> str:
    """Force the CSRF cookie to be issued and return its token.

    Returning the token supports an explicit CSRF bootstrap endpoint for
    deployments where the SPA and API are served from different origins and
    JavaScript cannot read the API-origin cookie.
    """
    from django.middleware.csrf import get_token

    return get_token(request)


def parse_bbox(raw: str | None) -> tuple[float, float, float, float] | None:
    if not raw:
        return None
    parts = [part.strip() for part in raw.split(",")]
    if len(parts) != 4:
        raise UnprocessableEntityError(
            "bbox must be min_lng,min_lat,max_lng,max_lat",
            details=[{"field": "bbox"}],
        )
    try:
        values = [float(part) for part in parts]
    except ValueError:
        raise UnprocessableEntityError("bbox values must be numbers.", details=[{"field": "bbox"}]) from None
    min_lng, min_lat, max_lng, max_lat = values
    if not (
        -180 <= min_lng <= 180
        and -180 <= max_lng <= 180
        and -90 <= min_lat <= 90
        and -90 <= max_lat <= 90
    ):
        raise UnprocessableEntityError("bbox out of range", details=[{"field": "bbox"}])
    if min_lng > max_lng or min_lat > max_lat:
        raise UnprocessableEntityError("bbox min must not exceed max", details=[{"field": "bbox"}])
    return min_lng, min_lat, max_lng, max_lat


def zero_if_none(value: Decimal | None) -> Decimal:
    return value if value is not None else Decimal("0")
