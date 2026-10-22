"""Campaign CRUD domain service (admin-managed)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models import Campaign, CampaignStatus, User
from app.services.audit_service import RequestContext, record_audit


def _validate_window(starts_at: datetime | None, ends_at: datetime | None, timezone_name: str) -> None:
    if starts_at and ends_at and starts_at > ends_at:
        raise AppError("Campaign start must be before its end.", details=[{"field": "ends_at"}])
    try:
        import zoneinfo

        zoneinfo.ZoneInfo(timezone_name)
    except Exception:
        raise AppError("Unknown timezone.", details=[{"field": "timezone"}]) from None


def create_campaign(db: Session, *, admin: User, data: dict, ctx: RequestContext) -> Campaign:
    _validate_window(data.get("starts_at"), data.get("ends_at"), data.get("timezone") or "UTC")
    existing = db.scalar(select(Campaign).where(Campaign.reference_code == data["reference_code"]))
    if existing is not None:
        raise AppError(
            "A campaign with this reference code already exists.", details=[{"field": "reference_code"}]
        )
    campaign = Campaign(
        name=data["name"],
        reference_code=data["reference_code"],
        starts_at=data.get("starts_at"),
        ends_at=data.get("ends_at"),
        status=CampaignStatus(data.get("status", CampaignStatus.DRAFT.value)),
        timezone=data.get("timezone") or "UTC",
        notes=data.get("notes"),
        created_by=admin.id,
    )
    db.add(campaign)
    record_audit(
        db,
        actor=admin,
        action="campaign.created",
        target_type="campaign",
        target_id=campaign.id,
        details={"reference_code": campaign.reference_code},
        ctx=ctx,
    )
    db.flush()
    return campaign


def update_campaign(
    db: Session, *, admin: User, campaign_id: uuid.UUID, data: dict, ctx: RequestContext
) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise NotFoundError("Campaign not found.")
    if (
        "status" in data
        and campaign.status == CampaignStatus.CLOSED
        and data["status"] != CampaignStatus.CLOSED.value
    ):
        raise AppError("Closed campaigns cannot be reopened; create a new campaign.", code="ILLEGAL_STATE")
    for key in ("name", "starts_at", "ends_at", "status", "timezone", "notes"):
        if key in data:
            setattr(campaign, key, data[key])
    _validate_window(campaign.starts_at, campaign.ends_at, campaign.timezone)
    record_audit(
        db,
        actor=admin,
        action="campaign.updated",
        target_type="campaign",
        target_id=campaign.id,
        details={"changed_fields": list(data.keys())},
        ctx=ctx,
    )
    db.flush()
    return campaign


def list_campaigns(
    db: Session, *, status: CampaignStatus | None, limit: int, offset: int
) -> tuple[list[Campaign], int]:
    stmt = select(Campaign)
    if status:
        stmt = stmt.where(Campaign.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(db.scalars(stmt.order_by(Campaign.created_at.desc()).limit(limit).offset(offset)))
    return rows, int(total)


def get_campaign(db: Session, campaign_id: uuid.UUID) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise NotFoundError("Campaign not found.")
    return campaign
