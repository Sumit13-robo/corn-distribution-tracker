"""Site routes (admin CRUD; distributor sees only assigned sites)."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import AdminDep, CurrentUserDep, PaginationDep, RequestCtx, get_db
from app.core.errors import NotFoundError
from app.models import DistributionRecord, DistributionSite, DistributorAssignment, RecordStatus
from app.schemas.common import Page, paginated
from app.schemas.sites import SiteIn, SiteOut, SitePatchIn, SiteProgressOut
from app.services import distribution_service, site_service

DbDep = Annotated[Session, Depends(get_db)]
router = APIRouter(tags=["sites"])


@router.get("/sites", response_model=Page[SiteOut])
def list_sites(
    user: CurrentUserDep,
    db: DbDep,
    pagination: PaginationDep,
    search: str | None = Query(default=None, max_length=120),
    campaign_id: uuid.UUID | None = Query(default=None),
    active_only: bool = Query(default=None),
):
    if user.is_admin:
        rows, total = site_service.list_sites(
            db,
            active_only=active_only if active_only is not None else False,
            search=search,
            campaign_id=campaign_id,
            limit=pagination.limit,
            offset=pagination.offset,
        )
    else:
        # Distributors see only sites with assignments (open or historically theirs).
        rows, total = _assigned_sites(db, user.user, pagination, search=search)
    return paginated(
        [
            SiteOut(
                id=s.id,
                name=s.name,
                site_code=s.site_code,
                address_text=s.address_text,
                region=s.region,
                latitude=s.latitude,
                longitude=s.longitude,
                geofence_radius_m=s.geofence_radius_m,
                max_acceptable_accuracy_m=s.max_acceptable_accuracy_m,
                is_active=s.is_active,
                notes=s.notes if user.is_admin else None,  # site notes are admin-internal
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in rows
        ],
        total,
        pagination.limit,
        pagination.offset,
    )


def _assigned_sites(db: Session, user, pagination, *, search: str | None):
    stmt = (
        select(DistributionSite)
        .join(DistributorAssignment, DistributorAssignment.site_id == DistributionSite.id)
        .where(DistributorAssignment.distributor_user_id == user.id)
    )
    if search:
        stmt = stmt.where(
            DistributionSite.name.ilike(f"%{search}%") | DistributionSite.site_code.ilike(f"%{search}%")
        )
    stmt = stmt.distinct()
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(DistributionSite.site_code).limit(pagination.limit).offset(pagination.offset)
        )
    )
    return rows, int(total)


@router.post("/sites", response_model=SiteOut, status_code=201)
def create_site(payload: SiteIn, admin: AdminDep, db: DbDep, ctx: RequestCtx):
    site = site_service.create_site(db, admin=admin.user, data=payload.model_dump(), ctx=ctx)
    db.commit()
    return SiteOut.model_validate(site)


@router.get("/sites/{site_id}", response_model=SiteOut)
def get_site(site_id: uuid.UUID, user: CurrentUserDep, db: DbDep):
    site = site_service.get_site(db, site_id)
    if not user.is_admin:
        assigned = db.scalar(
            select(func.count())
            .select_from(DistributorAssignment)
            .where(
                DistributorAssignment.site_id == site_id,
                DistributorAssignment.distributor_user_id == user.user.id,
            )
        )
        if not assigned:
            raise NotFoundError("Site not found.")
        if site.notes:
            site.notes = None
    return SiteOut.model_validate(site)


@router.get("/sites/{site_id}/progress", response_model=SiteProgressOut)
def site_progress(
    site_id: uuid.UUID, user: CurrentUserDep, db: DbDep, campaign_id: uuid.UUID | None = Query(default=None)
):
    # Existence check: unknown ids must 404 even before scoping.
    site_service.get_site(db, site_id)
    scope_user = None if user.is_admin else user.user
    if scope_user is not None:
        assigned = db.scalar(
            select(func.count())
            .select_from(DistributorAssignment)
            .where(
                DistributorAssignment.site_id == site_id,
                DistributorAssignment.distributor_user_id == user.user.id,
            )
        )
        if not assigned:
            raise NotFoundError("Site not found.")
    stmt = select(DistributionRecord).where(DistributionRecord.site_id == site_id)
    if scope_user is not None:
        stmt = stmt.where(DistributionRecord.distributor_user_id == scope_user.id)
    if campaign_id:
        stmt = stmt.where(DistributionRecord.campaign_id == campaign_id)
    records = list(db.scalars(stmt))
    target = Decimal(0)
    assignments_stmt = select(DistributorAssignment).where(DistributorAssignment.site_id == site_id)
    if scope_user is not None:
        assignments_stmt = assignments_stmt.where(DistributorAssignment.distributor_user_id == scope_user.id)
    if campaign_id:
        assignments_stmt = assignments_stmt.where(DistributorAssignment.campaign_id == campaign_id)
    for assignment in db.scalars(assignments_stmt):
        target += Decimal(assignment.target_quantity_kg)
    approved = sum((Decimal(r.quantity_kg) for r in records if r.status == RecordStatus.APPROVED), Decimal(0))
    pending = sum((Decimal(r.quantity_kg) for r in records if r.status == RecordStatus.SUBMITTED), Decimal(0))
    rejected = sum((Decimal(r.quantity_kg) for r in records if r.status == RecordStatus.REJECTED), Decimal(0))
    from app.models import PhotoEvidence

    evidence_present = False
    flagged = any(set(r.geo_flags or []) - {"LOCATION_EXCEPTION"} for r in records)
    if records:
        evidence_present = (
            db.scalar(
                select(func.count())
                .select_from(PhotoEvidence)
                .where(PhotoEvidence.distribution_record_id.in_([r.id for r in records]))
            )
            or 0
        ) > 0
    last_visit = distribution_service.last_visit_at(db, site_id=site_id)
    return SiteProgressOut(
        target_kg=target,
        submitted_kg=approved + pending + rejected,
        approved_kg=approved,
        pending_kg=pending,
        rejected_kg=rejected,
        remaining_target_kg=max(target - approved, Decimal(0)),
        submission_count=len(records),
        last_visit_at=last_visit,
        evidence_status="EVIDENCE_PRESENT"
        if evidence_present
        else ("NONE" if not records else "EVIDENCE_MISSING"),
        has_flagged_evidence=flagged,
    )


@router.patch("/sites/{site_id}", response_model=SiteOut)
def update_site(site_id: uuid.UUID, payload: SitePatchIn, admin: AdminDep, db: DbDep, ctx: RequestCtx):
    site = site_service.update_site(
        db, admin=admin.user, site_id=site_id, data=payload.model_dump(exclude_unset=True), ctx=ctx
    )
    db.commit()
    return SiteOut.model_validate(site)


@router.post("/sites/{site_id}/deactivate", response_model=SiteOut)
def deactivate_site(site_id: uuid.UUID, admin: AdminDep, db: DbDep, ctx: RequestCtx):
    site = site_service.deactivate_site(db, admin=admin.user, site_id=site_id, ctx=ctx)
    db.commit()
    return SiteOut.model_validate(site)
