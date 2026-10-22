"""Distribution records: distributor submissions of delivered quantity with review state.

Pending SUBMITTED records act as stock reservations (docs/INVENTORY_LEDGER.md):
available_kg = posted_balance - sum(submitted reservations). Approval posts exactly one
DELIVERY movement (unique `stock_movement_id`); rejection releases the reservation.
"""

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
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk
from app.models.enums import GeoStatus, RecordStatus


class DistributionRecord(TimestampMixin, Base):
    __tablename__ = "distribution_records"
    __table_args__ = (
        CheckConstraint("quantity_kg > 0", name="record_quantity_positive"),
        CheckConstraint(
            "(location_latitude IS NULL AND location_longitude IS NULL) OR "
            "(location_latitude >= -90 AND location_latitude <= 90 AND "
            "location_longitude >= -180 AND location_longitude <= 180)",
            name="record_coordinate_range",
        ),
        UniqueConstraint("distributor_user_id", "idempotency_key", name="uq_record_idempotency"),
        Index("ix_distribution_records_status", "status"),
        Index("ix_distribution_records_distributor_status", "distributor_user_id", "status"),
        Index("ix_distribution_records_site", "site_id"),
        Index("ix_distribution_records_campaign", "campaign_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"))
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("distributor_assignments.id", ondelete="RESTRICT"), nullable=False
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("distribution_sites.id", ondelete="RESTRICT"), nullable=False
    )
    distributor_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, native_enum=False, length=20, name="record_status"),
        nullable=False,
        default=RecordStatus.SUBMITTED,
    )
    # Client-generated stable idempotency key; unique per submitting user.
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    client_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    review_reason: Mapped[str | None] = mapped_column(String(2000))
    stock_movement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stock_movements.id", ondelete="RESTRICT"), unique=True
    )
    notes: Mapped[str | None] = mapped_column(String(2000))
    location_latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    location_longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    location_accuracy_m: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    location_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    device_reported_location_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    distance_to_site_m: Mapped[Decimal | None] = mapped_column(Numeric(12, 1))
    geo_status: Mapped[GeoStatus] = mapped_column(
        Enum(GeoStatus, native_enum=False, length=20, name="geo_status"),
        nullable=False,
        default=GeoStatus.UNAVAILABLE,
    )
    geo_flags: Mapped[list] = mapped_column(postgresql.JSONB, default=list, nullable=False)
    review_exception_reason: Mapped[str | None] = mapped_column(String(2000))
