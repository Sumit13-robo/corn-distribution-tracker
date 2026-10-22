"""Delivery (distribution record) routes: submit, list/detail, approve, reject, cancel."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import AdminDep, CurrentUserDep, PaginationDep, RequestCtx, get_db
from app.models import DistributionRecord, PhotoEvidence, RecordStatus
from app.schemas.common import Page, paginated
from app.schemas.distributions import (
    ApprovalIn,
    CancelIn,
    DeliveryCreateIn,
    DistributionOut,
    EvidenceOut,
    RejectIn,
)
from app.services import distribution_service

DbDep = Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/deliveries", tags=["deliveries"])


def _record_out(db: Session, record: DistributionRecord) -> DistributionOut:
    evidence_rows = list(
        db.scalars(select(PhotoEvidence).where(PhotoEvidence.distribution_record_id == record.id))
    )
    return DistributionOut(
        id=record.id,
        campaign_id=record.campaign_id,
        assignment_id=record.assignment_id,
        site_id=record.site_id,
        distributor_user_id=record.distributor_user_id,
        quantity_kg=record.quantity_kg,
        status=record.status.value,
        client_created_at=record.client_created_at,
        submitted_at=record.submitted_at,
        reviewed_at=record.reviewed_at,
        reviewed_by=record.reviewed_by,
        review_reason=record.review_reason,
        review_exception_reason=record.review_exception_reason,
        stock_movement_id=record.stock_movement_id,
        notes=record.notes,
        location_latitude=record.location_latitude,
        location_longitude=record.location_longitude,
        location_accuracy_m=record.location_accuracy_m,
        location_timestamp=record.location_timestamp,
        device_reported_location_time=record.device_reported_location_time,
        distance_to_site_m=record.distance_to_site_m,
        geo_status=record.geo_status.value,
        geo_flags=list(record.geo_flags or []),
        evidence=[EvidenceOut.model_validate(ev) for ev in evidence_rows],
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post("", response_model=DistributionOut, status_code=201)
def submit_delivery(
    payload: DeliveryCreateIn,
    user: CurrentUserDep,
    db: DbDep,
    ctx: RequestCtx,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    key = idempotency_key or f"delivery:{uuid.uuid4()}"
    if len(key) > 64:
        key = key[:64]
    # The service returns (record, is_duplicate); retries return the original row.
    record, _ = distribution_service.submit_delivery(
        db,
        user=user.user,
        assignment_id=payload.assignment_id,
        quantity=payload.quantity,
        unit=payload.unit,
        notes=payload.notes,
        evidence_specs=[spec.model_dump() for spec in payload.evidence],
        location=payload.location.model_dump() if payload.location else None,
        idempotency_key=key,
        ctx=ctx,
    )
    db.commit()
    return _record_out(db, record)


@router.get("", response_model=Page[DistributionOut])
def list_deliveries(
    user: CurrentUserDep,
    db: DbDep,
    pagination: PaginationDep,
    status: str | None = Query(default=None, max_length=20),
    campaign_id: uuid.UUID | None = Query(default=None),
    site_id: uuid.UUID | None = Query(default=None),
    distributor_user_id: uuid.UUID | None = Query(default=None),
    from_ts: Annotated[datetime | None, Query(alias="from")] = None,
    to_ts: Annotated[datetime | None, Query(alias="to")] = None,
):
    record_status = RecordStatus(status) if status else None
    stmt = distribution_service.scope_records_query(
        db,
        user=user.user,
        status=record_status,
        campaign_id=campaign_id,
        site_id=site_id,
        distributor_user_id=distributor_user_id,
        from_ts=from_ts,
        to_ts=to_ts,
    )
    from sqlalchemy import func

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(DistributionRecord.submitted_at.desc())
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
    )
    # _record_out already hydrates each record's evidence.
    items = [_record_out(db, record) for record in rows]
    return paginated(items, int(total), pagination.limit, pagination.offset)


@router.get("/{record_id}", response_model=DistributionOut)
def get_delivery(record_id: uuid.UUID, user: CurrentUserDep, db: DbDep):
    record = distribution_service.get_record_scoped(db, user=user.user, record_id=record_id)
    return _record_out(db, record)


@router.post("/{record_id}/approve", response_model=DistributionOut)
def approve_delivery(
    record_id: uuid.UUID,
    payload: ApprovalIn,
    admin: AdminDep,
    db: DbDep,
    ctx: RequestCtx,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    record, _duplicate = distribution_service.approve_delivery(
        db,
        admin=admin.user,
        record_id=record_id,
        exception_reason=payload.exception_reason,
        review_note=payload.review_note,
        idempotency_key=idempotency_key,
        ctx=ctx,
    )
    db.commit()
    return _record_out(db, record)


@router.post("/{record_id}/reject", response_model=DistributionOut)
def reject_delivery(record_id: uuid.UUID, payload: RejectIn, admin: AdminDep, db: DbDep, ctx: RequestCtx):
    record, _duplicate = distribution_service.reject_delivery(
        db, admin=admin.user, record_id=record_id, reason=payload.reason, ctx=ctx
    )
    db.commit()
    return _record_out(db, record)


@router.post("/{record_id}/cancel", response_model=DistributionOut)
def cancel_delivery(
    record_id: uuid.UUID, payload: CancelIn, user: CurrentUserDep, db: DbDep, ctx: RequestCtx
):
    record, _duplicate = distribution_service.cancel_delivery(
        db, actor=user.user, record_id=record_id, reason=payload.reason, ctx=ctx
    )
    db.commit()
    return _record_out(db, record)
