"""Audit trail writer/reader. Events are append-only; no edit/delete API."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.db.models import QuerySet

from ..models import AuditEvent, User


@dataclass
class RequestContext:
    request_id: str | None = None
    ip: str | None = None
    user_agent: str | None = None


def client_ip(request) -> str | None:
    """Return the audit/rate-limit source address.

    Forwarded headers are attacker-controlled unless a trusted reverse proxy
    overwrites them. Only read X-Forwarded-For when explicitly configured.
    """
    from django.conf import settings

    remote = request.META.get("REMOTE_ADDR")
    if settings.TRUST_X_FORWARDED_FOR:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # The edge proxy must overwrite this header with the immediate
            # client address. Use the first value for compatibility with
            # proxies that append, but never trust it without the opt-in.
            return forwarded.split(",", 1)[0].strip()[:64]
    return remote[:64] if remote else None


def context_from_request(request, *, include_forwarded: bool = True) -> RequestContext:
    ip = client_ip(request) if include_forwarded else request.META.get("REMOTE_ADDR")
    return RequestContext(
        request_id=getattr(request, "request_id", None),
        ip=ip,
        user_agent=(request.headers.get("user-agent") or "")[:200] or None,
    )


def record_audit(
    *,
    actor: User | uuid.UUID | None,
    action: str,
    target_type: str,
    target_id: uuid.UUID | None = None,
    reason: str | None = None,
    details: dict[str, Any] | None = None,
    ctx: RequestContext | None = None,
) -> AuditEvent:
    actor_id = actor.id if isinstance(actor, User) else actor
    return AuditEvent.objects.create(
        actor_user_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        details=details or {},
        request_id=ctx.request_id if ctx else None,
        ip_address=ctx.ip if ctx else None,
        user_agent_abridged=(ctx.user_agent[:200] if ctx and ctx.user_agent else None),
    )


def list_audit_events(
    *,
    action: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
    limit: int = 25,
    offset: int = 0,
) -> tuple[QuerySet[AuditEvent], int]:
    qs = AuditEvent.objects.all()
    if action:
        qs = qs.filter(action=action)
    if actor_user_id:
        qs = qs.filter(actor_user_id=actor_user_id)
    if target_type:
        qs = qs.filter(target_type=target_type)
    if target_id:
        qs = qs.filter(target_id=target_id)
    if occurred_from:
        qs = qs.filter(occurred_at__gte=occurred_from)
    if occurred_to:
        qs = qs.filter(occurred_at__lte=occurred_to)
    total = qs.count()
    return qs.order_by("-occurred_at")[offset : offset + limit], total
