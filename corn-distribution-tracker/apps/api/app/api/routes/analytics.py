"""Analytics + export routes (admin-only breakdowns; overview is role-scoped)."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import AdminDep, CurrentUserDep, RequestCtx, get_db
from app.models import DistributionRecord, DistributionSite, RecordStatus, User
from app.schemas.analytics import DistributorPerfOut, MapSiteOut, OverviewOut, SitePerfOut
from app.services import analytics_service
from app.services.audit_service import record_audit

DbDep = Annotated[Session, Depends(get_db)]
router = APIRouter(tags=["analytics"])


def _parse_bbox(bbox: str | None) -> tuple[float, float, float, float] | None:
    if not bbox:
        return None
    parts = [p.strip() for p in bbox.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox must be min_lng,min_lat,max_lng,max_lat")
    values = [float(p) for p in parts]
    min_lng, min_lat, max_lng, max_lat = values
    if not (
        -180 <= min_lng <= 180 and -180 <= max_lng <= 180 and -90 <= min_lat <= 90 and -90 <= max_lat <= 90
    ):
        raise ValueError("bbox out of range")
    if min_lng > max_lng or min_lat > max_lat:
        raise ValueError("bbox min must not exceed max")
    return min_lng, min_lat, max_lng, max_lat


@router.get("/analytics/overview", response_model=OverviewOut)
def overview(
    user: CurrentUserDep,
    db: DbDep,
    campaign_id: uuid.UUID | None = Query(default=None),
    from_ts: Annotated[datetime | None, Query(alias="from")] = None,
    to_ts: Annotated[datetime | None, Query(alias="to")] = None,
):
    scope_user = None if user.is_admin else user.user
    data = analytics_service.overview(
        db, scope_user=scope_user, campaign_id=campaign_id, from_ts=from_ts, to_ts=to_ts
    )
    return OverviewOut.model_validate(data)


@router.get("/analytics/distributors", response_model=list[DistributorPerfOut])
def distributors_analytics(
    admin: AdminDep,
    db: DbDep,
    campaign_id: uuid.UUID | None = Query(default=None),
    from_ts: Annotated[datetime | None, Query(alias="from")] = None,
    to_ts: Annotated[datetime | None, Query(alias="to")] = None,
):
    rows = analytics_service.distributor_performance(
        db, campaign_id=campaign_id, from_ts=from_ts, to_ts=to_ts
    )
    return [DistributorPerfOut.model_validate(r) for r in rows]


@router.get("/analytics/sites", response_model=list[SitePerfOut])
def sites_analytics(
    admin: AdminDep,
    db: DbDep,
    campaign_id: uuid.UUID | None = Query(default=None),
    from_ts: Annotated[datetime | None, Query(alias="from")] = None,
    to_ts: Annotated[datetime | None, Query(alias="to")] = None,
):
    rows = analytics_service.site_performance(db, campaign_id=campaign_id, from_ts=from_ts, to_ts=to_ts)
    return [SitePerfOut.model_validate(r) for r in rows]


@router.get("/analytics/map-sites", response_model=list[MapSiteOut])
def map_sites(
    admin: AdminDep,
    db: DbDep,
    bbox: str | None = Query(default=None, max_length=120),
    campaign_id: uuid.UUID | None = Query(default=None),
    distributor_user_id: uuid.UUID | None = Query(default=None),
):
    try:
        parsed_bbox = _parse_bbox(bbox)
    except ValueError as exc:
        from app.core.errors import UnprocessableEntityError

        raise UnprocessableEntityError(str(exc), details=[{"field": "bbox"}]) from None
    rows = analytics_service.map_sites(
        db, bbox=parsed_bbox, campaign_id=campaign_id, distributor_user_id=distributor_user_id
    )
    return [MapSiteOut.model_validate(r) for r in rows]


@router.get("/exports/distributions.csv")
def export_distributions_csv(
    admin: AdminDep,
    db: DbDep,
    ctx: RequestCtx,
    campaign_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None, max_length=20),
    distributor_user_id: uuid.UUID | None = Query(default=None),
    from_ts: Annotated[datetime | None, Query(alias="from")] = None,
    to_ts: Annotated[datetime | None, Query(alias="to")] = None,
):
    record_status = RecordStatus(status) if status else None
    from app.services.distribution_service import scope_records_query

    stmt = scope_records_query(
        db,
        user=admin.user,
        status=record_status,
        campaign_id=campaign_id,
        site_id=None,
        distributor_user_id=distributor_user_id,
        from_ts=from_ts,
        to_ts=to_ts,
    )
    records = list(db.scalars(stmt.order_by(DistributionRecord.submitted_at.desc()).limit(10_000)))
    sites = {s.id: s for s in db.scalars(select(DistributionSite))}
    distributors = {u.id: u for u in db.scalars(select(User).where(User.role == "DISTRIBUTOR"))}

    def safe_cell(value: str) -> str:
        if value.startswith(("=", "+", "-", "@")):
            return "'" + value
        return value

    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(
        [
            "record_id",
            "submitted_at",
            "status",
            "site_code",
            "site_name",
            "distributor_email",
            "quantity_kg",
            "geo_status",
            "geo_flags",
            "review_reason",
            "stock_movement_id",
        ]
    )
    timezone_suffix = "-utc"
    for record in records:
        site = sites.get(record.site_id)
        distributor = distributors.get(record.distributor_user_id)
        writer.writerow(
            [
                safe_cell(str(record.id)),
                record.submitted_at.isoformat() + timezone_suffix if record.submitted_at else "",
                record.status.value,
                safe_cell(site.site_code if site else ""),
                safe_cell(site.name if site else ""),
                safe_cell(distributor.email_normalized if distributor else ""),
                str(record.quantity_kg),
                record.geo_status.value,
                safe_cell(",".join(record.geo_flags or [])),
                safe_cell(record.review_reason or ""),
                str(record.stock_movement_id or ""),
            ]
        )
    record_audit(
        db,
        actor=admin.user,
        action="export.distributions",
        target_type="distribution_record",
        details={
            "count": len(records),
            "filters": {
                "campaign_id": str(campaign_id) if campaign_id else None,
                "status": status,
                "distributor_user_id": str(distributor_user_id) if distributor_user_id else None,
            },
        },
        ctx=ctx,
    )
    db.commit()
    buffer.seek(0)
    content_disposition = "attachment; filename=\"distributions.csv\"; filename*=UTF-8''distributions.csv"
    return StreamingResponse(
        io.BytesIO(buffer.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": content_disposition},
    )
