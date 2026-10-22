"""Campaign routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import AdminDep, CurrentUserDep, PaginationDep, RequestCtx, get_db
from app.models import CampaignStatus
from app.schemas.campaigns import CampaignIn, CampaignOut, CampaignPatchIn
from app.schemas.common import Page, paginated
from app.services import campaign_service

DbDep = Annotated[Session, Depends(get_db)]
router = APIRouter(tags=["campaigns"])


@router.get("/campaigns", response_model=Page[CampaignOut])
def list_campaigns(
    user: CurrentUserDep,
    db: DbDep,
    pagination: PaginationDep,
    status: str | None = Query(default=None, max_length=20),
):
    campaign_status = CampaignStatus(status) if status else None
    rows, total = campaign_service.list_campaigns(
        db, status=campaign_status, limit=pagination.limit, offset=pagination.offset
    )
    return paginated(
        [CampaignOut.model_validate(c) for c in rows], total, pagination.limit, pagination.offset
    )


@router.post("/campaigns", response_model=CampaignOut, status_code=201)
def create_campaign(payload: CampaignIn, admin: AdminDep, db: DbDep, ctx: RequestCtx):
    campaign = campaign_service.create_campaign(db, admin=admin.user, data=payload.model_dump(), ctx=ctx)
    db.commit()
    return CampaignOut.model_validate(campaign)


@router.get("/campaigns/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: uuid.UUID, user: CurrentUserDep, db: DbDep):
    return CampaignOut.model_validate(campaign_service.get_campaign(db, campaign_id))


@router.patch("/campaigns/{campaign_id}", response_model=CampaignOut)
def update_campaign(
    campaign_id: uuid.UUID,
    payload: CampaignPatchIn,
    admin: AdminDep,
    db: DbDep,
    ctx: RequestCtx,
):
    campaign = campaign_service.update_campaign(
        db, admin=admin.user, campaign_id=campaign_id, data=payload.model_dump(exclude_unset=True), ctx=ctx
    )
    db.commit()
    return CampaignOut.model_validate(campaign)
