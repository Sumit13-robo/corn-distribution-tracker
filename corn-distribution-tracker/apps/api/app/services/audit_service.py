"""Audit writer + reader services. Audit events are append-only; no edit/delete APIs."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditEvent, User


@dataclass
class RequestContext:
    request_id: str | None = None
    ip: str | None = None
    user_agent: str | None = None


def record_audit(
    db: Session,
    *,
    actor: User | uuid.UUID | None,
    action: str,
    target_type: str,
    target_id: uuid.UUID | None = None,
    reason: str | None = None,
    details: dict[str, Any] | None = None,
    ctx: RequestContext | None = None,
) -> None:
    """Append an audit event in the caller's transaction (rolls back with it)."""
    actor_id: uuid.UUID | None
    if isinstance(actor, User):
        actor_id = actor.id
    else:
        actor_id = actor
    event = AuditEvent(
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
    db.add(event)


def list_audit_events(
    db: Session,
    *,
    action: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
    limit: int = 25,
    offset: int = 0,
) -> tuple[list[AuditEvent], int]:
    stmt = select(AuditEvent)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    if actor_user_id:
        stmt = stmt.where(AuditEvent.actor_user_id == actor_user_id)
    if target_type:
        stmt = stmt.where(AuditEvent.target_type == target_type)
    if target_id:
        stmt = stmt.where(AuditEvent.target_id == target_id)
    if occurred_from:
        stmt = stmt.where(AuditEvent.occurred_at >= occurred_from)
    if occurred_to:
        stmt = stmt.where(AuditEvent.occurred_at <= occurred_to)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.execute(stmt.order_by(AuditEvent.occurred_at.desc()).limit(limit).offset(offset)).scalars()
    )
    return rows, int(total)
