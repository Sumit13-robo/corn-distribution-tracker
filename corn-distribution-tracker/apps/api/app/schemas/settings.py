"""Organization settings schemas (allowlisted fields)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field

from app.schemas.common import ApiModel


class SettingsOut(ApiModel):
    timezone: str
    default_display_unit: str
    kg_per_bag: Decimal | None = None
    default_geofence_radius_m: int
    max_acceptable_gps_accuracy_m: int
    max_location_age_seconds: int
    max_capture_time_drift_seconds: int
    updated_at: datetime | None = None


class SettingsPatchIn(ApiModel):
    """Admin patch input. Unknown keys are REJECTED: strictly allowlisted fields."""

    model_config = ConfigDict(extra="forbid")

    timezone: str | None = Field(default=None, max_length=64)
    default_display_unit: str | None = Field(default=None, max_length=12)
    kg_per_bag: Decimal | None = Field(default=None, gt=0, le=1000)
    default_geofence_radius_m: int | None = Field(default=None, gt=0, le=100_000)
    max_acceptable_gps_accuracy_m: int | None = Field(default=None, gt=0, le=5000)
    max_location_age_seconds: int | None = Field(default=None, gt=0, le=86400)
    max_capture_time_drift_seconds: int | None = Field(default=None, gt=0, le=86400)
