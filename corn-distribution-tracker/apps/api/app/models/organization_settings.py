"""Single-row organization settings for the initial single-organization release.

Strictly allowlisted fields only - infrastructure secrets stay in environment/secrets
manager and are never UI-editable (docs/architecture/API_CONTRACT.md).
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk
from app.models.enums import DisplayUnit


class OrganizationSettings(TimestampMixin, Base):
    __tablename__ = "organization_settings"
    __table_args__ = (
        CheckConstraint(
            "kg_per_bag IS NULL OR (kg_per_bag > 0 AND kg_per_bag <= 1000)", name="kg_per_bag_range"
        ),
        CheckConstraint("default_geofence_radius_m > 0", name="geofence_radius_positive"),
        CheckConstraint("max_acceptable_gps_accuracy_m > 0", name="gps_accuracy_positive"),
        CheckConstraint("max_location_age_seconds > 0", name="location_age_positive"),
        CheckConstraint("max_capture_time_drift_seconds > 0", name="capture_drift_positive"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    default_display_unit: Mapped[DisplayUnit] = mapped_column(
        Enum(DisplayUnit, native_enum=False, length=12, name="display_unit"),
        nullable=False,
        default=DisplayUnit.KG,
    )
    kg_per_bag: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    default_geofence_radius_m: Mapped[int] = mapped_column(nullable=False)
    max_acceptable_gps_accuracy_m: Mapped[int] = mapped_column(nullable=False)
    max_location_age_seconds: Mapped[int] = mapped_column(nullable=False)
    max_capture_time_drift_seconds: Mapped[int] = mapped_column(nullable=False, default=600)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
