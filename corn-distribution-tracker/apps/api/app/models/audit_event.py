"""Append-only audit trail of important actions (never passwords/tokens/URLs/bytes)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, uuid_pk


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_occurred", "occurred_at"),
        Index("ix_audit_events_action", "action"),
        Index("ix_audit_events_target", "target_type", "target_id"),
        Index("ix_audit_events_actor", "actor_user_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column()
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    request_id: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(String(2000))
    details: Mapped[dict | None] = mapped_column(postgresql.JSONB, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent_abridged: Mapped[str | None] = mapped_column(String(200))
