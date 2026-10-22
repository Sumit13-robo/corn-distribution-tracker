"""Site schemas with coordinate validation at the boundary."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import ApiModel


class SiteIn(ApiModel):
    name: str = Field(min_length=1, max_length=160)
    site_code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    address_text: str | None = Field(default=None, max_length=500)
    region: str | None = Field(default=None, max_length=120)
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)
    geofence_radius_m: int = Field(default=200, gt=0, le=100_000)
    max_acceptable_accuracy_m: int | None = Field(default=None, gt=0, le=5000)
    notes: str | None = Field(default=None, max_length=2000)


class SitePatchIn(SiteIn):
    name: str | None = Field(default=None, min_length=1, max_length=160)  # type: ignore[assignment]
    site_code: str | None = None  # type: ignore[assignment]
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)  # type: ignore[assignment]
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)  # type: ignore[assignment]
    geofence_radius_m: int | None = Field(default=None, gt=0, le=100_000)  # type: ignore[assignment]
    max_acceptable_accuracy_m: int | None = None
    is_active: bool | None = None


class SiteOut(ApiModel):
    id: uuid.UUID
    name: str
    site_code: str
    address_text: str | None = None
    region: str | None = None
    latitude: Decimal
    longitude: Decimal
    geofence_radius_m: int
    max_acceptable_accuracy_m: int | None = None
    is_active: bool
    notes: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class SiteProgressOut(ApiModel):
    target_kg: Decimal
    submitted_kg: Decimal
    approved_kg: Decimal
    pending_kg: Decimal
    rejected_kg: Decimal
    remaining_target_kg: Decimal
    submission_count: int
    last_visit_at: datetime | None = None
    evidence_status: str
    has_flagged_evidence: bool
