"""Audit trail + organization settings routes."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import AdminDep, CurrentUserDep, PaginationDep, RequestCtx, get_db
from app.schemas.audit import AuditEventOut
from app.schemas.common import Page, paginated
from app.schemas.settings import SettingsOut, SettingsPatchIn
from app.services import audit_service, settings_service

DbDep = Annotated[Session, Depends(get_db)]
router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=SettingsOut)
def get_settings_route(user: CurrentUserDep, db: DbDep):
    settings = settings_service.get_or_create_settings(db)
    return SettingsOut(
        timezone=settings.timezone,
        default_display_unit=settings.default_display_unit.value,
        kg_per_bag=settings.kg_per_bag,
        default_geofence_radius_m=settings.default_geofence_radius_m,
        max_acceptable_gps_accuracy_m=settings.max_acceptable_gps_accuracy_m,
        max_location_age_seconds=settings.max_location_age_seconds,
        max_capture_time_drift_seconds=settings.max_capture_time_drift_seconds,
        updated_at=settings.updated_at,
    )


@router.patch("/settings", response_model=SettingsOut)
def patch_settings(payload: SettingsPatchIn, admin: AdminDep, db: DbDep, ctx: RequestCtx):
    settings = settings_service.update_settings(
        db, admin=admin.user, payload=payload.model_dump(exclude_unset=True), ctx=ctx
    )
    db.commit()
    db.refresh(settings)
    return SettingsOut(
        timezone=settings.timezone,
        default_display_unit=settings.default_display_unit.value,
        kg_per_bag=settings.kg_per_bag,
        default_geofence_radius_m=settings.default_geofence_radius_m,
        max_acceptable_gps_accuracy_m=settings.max_acceptable_gps_accuracy_m,
        max_location_age_seconds=settings.max_location_age_seconds,
        max_capture_time_drift_seconds=settings.max_capture_time_drift_seconds,
        updated_at=settings.updated_at,
    )


@router.get("/audit/events", response_model=Page[AuditEventOut])
def audit_events(
    admin: AdminDep,
    db: DbDep,
    pagination: PaginationDep,
    action: str | None = Query(default=None, max_length=80),
    actor_user_id: uuid.UUID | None = Query(default=None),
    target_type: str | None = Query(default=None, max_length=40),
    target_id: uuid.UUID | None = Query(default=None),
    occurred_from: Annotated[datetime | None, Query(alias="from")] = None,
    occurred_to: Annotated[datetime | None, Query(alias="to")] = None,
):
    rows, total = audit_service.list_audit_events(
        db,
        action=action,
        actor_user_id=actor_user_id,
        target_type=target_type,
        target_id=target_id,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return paginated(
        [AuditEventOut.model_validate(ev) for ev in rows], total, pagination.limit, pagination.offset
    )
