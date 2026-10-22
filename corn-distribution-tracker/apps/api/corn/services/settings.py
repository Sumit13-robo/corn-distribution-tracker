"""Organization settings singleton with an allowlisted, audited update path."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.conf import settings as django_settings

from ..errors import AppError
from ..models import OrganizationSettings, User
from .audit import RequestContext, record_audit

ALLOWED_SETTINGS = {
    "timezone",
    "default_display_unit",
    "kg_per_bag",
    "default_geofence_radius_m",
    "max_acceptable_gps_accuracy_m",
    "max_location_age_seconds",
    "max_capture_time_drift_seconds",
}


def get_or_create_settings() -> OrganizationSettings:
    settings_row = OrganizationSettings.objects.first()
    if settings_row is None:
        settings_row = OrganizationSettings.objects.create(
            timezone=django_settings.ORG_TIMEZONE,
            default_geofence_radius_m=django_settings.DEFAULT_GEOFENCE_RADIUS_M,
            max_acceptable_gps_accuracy_m=django_settings.MAX_ACCEPTABLE_GPS_ACCURACY_M,
            max_location_age_seconds=django_settings.MAX_LOCATION_AGE_SECONDS,
            max_capture_time_drift_seconds=django_settings.MAX_CAPTURE_TIME_DRIFT_SECONDS,
        )
    return settings_row


def update_settings(
    *, admin: User, payload: dict[str, Any], ctx: RequestContext
) -> OrganizationSettings:
    settings_row = get_or_create_settings()
    unknown = set(payload) - ALLOWED_SETTINGS
    if unknown:
        raise AppError(
            f"Unsupported setting keys: {sorted(unknown)}",
            details=[{"field": key} for key in sorted(unknown)],
        )
    if not payload:
        raise AppError("No settings provided", details=[])
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    for key, value in payload.items():
        current = getattr(settings_row, key)
        if isinstance(current, Decimal) or key == "kg_per_bag":
            value = Decimal(str(value)) if value is not None else None
        before[key] = str(current) if isinstance(current, Decimal) else current
        after[key] = str(value) if isinstance(value, Decimal) else value
        setattr(settings_row, key, value)
    settings_row.updated_by = admin
    settings_row.save()
    record_audit(
        actor=admin,
        action="settings.updated",
        target_type="organization_settings",
        target_id=settings_row.id,
        details={"before": before, "after": after},
        ctx=ctx,
    )
    return settings_row
