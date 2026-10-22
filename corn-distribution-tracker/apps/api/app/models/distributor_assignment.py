"""Distributor assignments: distributor + campaign + site + target quantity (kg)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk
from app.models.enums import AssignmentStatus


class DistributorAssignment(TimestampMixin, Base):
    __tablename__ = "distributor_assignments"
    __table_args__ = (
        CheckConstraint("target_quantity_kg > 0", name="assignment_target_positive"),
        # Explicit policy (DOMAIN_MODEL): at most one open (ACTIVE/PAUSED) assignment per
        # (campaign, site, distributor). Completed assignments may be followed by a new one.
        Index(
            "uq_assignment_open",
            "campaign_id",
            "site_id",
            "distributor_user_id",
            unique=True,
            postgresql_where=sa_text("status IN ('ACTIVE', 'PAUSED')"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"))
    site_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("distribution_sites.id", ondelete="CASCADE"), nullable=False
    )
    distributor_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_quantity_kg: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus, native_enum=False, length=20, name="assignment_status"),
        nullable=False,
        default=AssignmentStatus.ACTIVE,
    )
    notes: Mapped[str | None] = mapped_column(String(1000))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
