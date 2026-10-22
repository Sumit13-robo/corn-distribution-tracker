"""Distribution sites: physical delivery points with expected WGS84 coordinates.

Coordinates are stored as validated numeric columns (SRID WGS84 assumption is stated
in docs/architecture/STACK_AND_REPO.md); distance calculations use the reviewed
geodesic helper in app/services/geo_service.py. When PostGIS is available in the
deployment database the optional extension is created in the initial migration,
and bbox filtering uses simple validated numeric range predicates.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class DistributionSite(TimestampMixin, Base):
    __tablename__ = "distribution_sites"
    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="site_lat_range"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="site_lng_range"),
        CheckConstraint("geofence_radius_m > 0", name="site_geofence_positive"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    site_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    address_text: Mapped[str | None] = mapped_column(String(500))
    region: Mapped[str | None] = mapped_column(String(120))
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    geofence_radius_m: Mapped[int] = mapped_column(nullable=False, default=200)
    max_acceptable_accuracy_m: Mapped[int | None] = mapped_column()
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
