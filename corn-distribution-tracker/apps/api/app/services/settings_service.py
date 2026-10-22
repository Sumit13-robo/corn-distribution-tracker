"""Organization settings service: singleton row with allowlisted, audited fields."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import OrganizationSettings, User
from app.services.audit_service import RequestContext, record_audit

ALLOWED_SETTINGS = {
    "timezone",
    "default_display_unit",
    "kg_per_bag",
    "default_geofence_radius_m",
    "max_acceptable_gps_accuracy_m",
    "max_location_age_seconds",
    "max_capture_time_drift_seconds",
}


def get_or_create_settings(db: Session) -> OrganizationSettings:
    settings = db.scalar(select(OrganizationSettings).limit(1))
    if settings is None:
        defaults = get_settings()
        settings = OrganizationSettings(
            timezone=defaults.org_timezone,
            default_geofence_radius_m=defaults.default_geofence_radius_m,
            max_acceptable_gps_accuracy_m=defaults.max_acceptable_gps_accuracy_m,
            max_location_age_seconds=defaults.max_location_age_seconds,
            max_capture_time_drift_seconds=defaults.max_capture_time_drift_seconds,
        )
        db.add(settings)
        db.flush()
    return settings


def update_settings(
    db: Session, admin: User, payload: dict[str, Any], ctx: RequestContext
) -> OrganizationSettings:
    settings = get_or_create_settings(db)
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    unknown = set(payload) - ALLOWED_SETTINGS
    if unknown:
        raise AppError(
            f"Unsupported setting keys: {sorted(unknown)}",
            details=[{"field": key} for key in sorted(unknown)],
        )
    if not payload:
        raise AppError("No settings provided", details=[])
    for key, value in payload.items():
        current = getattr(settings, key)
        if isinstance(current, Decimal):
            value = Decimal(str(value)) if value is not None else None
        before[key] = str(current) if isinstance(current, Decimal) else current
        after[key] = str(value) if isinstance(value, Decimal) else value
        setattr(settings, key, value)
    settings.updated_by = admin.id
    settings.updated_at = datetime.now(UTC)
    record_audit(
        db,
        actor=admin,
        action="settings.updated",
        target_type="organization_settings",
        target_id=settings.id,
        details={"before": before, "after": after},
        ctx=ctx,
    )
    db.flush()
    return settings
