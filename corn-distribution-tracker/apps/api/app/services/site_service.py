"""Site domain service: coordinate-validated CRUD with location-change audit."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models import DistributionSite, User
from app.services.audit_service import RequestContext, record_audit
from app.services.geo_service import validate_coordinates


def create_site(db: Session, *, admin: User, data: dict, ctx: RequestContext) -> DistributionSite:
    lat, lng = validate_coordinates(Decimal(str(data["latitude"])), Decimal(str(data["longitude"])))
    existing = db.scalar(select(DistributionSite).where(DistributionSite.site_code == data["site_code"]))
    if existing is not None:
        raise AppError("A site with this code already exists.", details=[{"field": "site_code"}])
    site = DistributionSite(
        name=data["name"],
        site_code=data["site_code"],
        address_text=data.get("address_text"),
        region=data.get("region"),
        latitude=lat,
        longitude=lng,
        geofence_radius_m=data.get("geofence_radius_m") or 200,
        max_acceptable_accuracy_m=data.get("max_acceptable_accuracy_m"),
        is_active=True,
        notes=data.get("notes"),
        created_by=admin.id,
    )
    db.add(site)
    record_audit(
        db,
        actor=admin,
        action="site.created",
        target_type="site",
        target_id=site.id,
        details={"site_code": site.site_code, "latitude": str(lat), "longitude": str(lng)},
        ctx=ctx,
    )
    db.flush()
    return site


def update_site(
    db: Session, *, admin: User, site_id: uuid.UUID, data: dict, ctx: RequestContext
) -> DistributionSite:
    site = db.get(DistributionSite, site_id)
    if site is None:
        raise NotFoundError("Site not found.")
    location_changed = False
    before = {"latitude": str(site.latitude), "longitude": str(site.longitude)}
    for key in (
        "name",
        "address_text",
        "region",
        "notes",
        "geofence_radius_m",
        "max_acceptable_accuracy_m",
        "is_active",
    ):
        if key in data:
            setattr(site, key, data[key])
    if "latitude" in data or "longitude" in data:
        lat = Decimal(str(data.get("latitude", site.latitude)))
        lng = Decimal(str(data.get("longitude", site.longitude)))
        site.latitude, site.longitude = validate_coordinates(lat, lng)
        location_changed = before != {"latitude": str(site.latitude), "longitude": str(site.longitude)}
    if location_changed or "geofence_radius_m" in data:
        record_audit(
            db,
            actor=admin,
            action="site.location_changed",
            target_type="site",
            target_id=site.id,
            details={
                "before": before,
                "after": {"latitude": str(site.latitude), "longitude": str(site.longitude)},
                "geofence_radius_m": site.geofence_radius_m,
            },
            ctx=ctx,
        )
    record_audit(
        db,
        actor=admin,
        action="site.updated",
        target_type="site",
        target_id=site.id,
        details={"changed_fields": list(data.keys())},
        ctx=ctx,
    )
    db.flush()
    return site


def deactivate_site(db: Session, *, admin: User, site_id: uuid.UUID, ctx: RequestContext) -> DistributionSite:
    site = db.get(DistributionSite, site_id)
    if site is None:
        raise NotFoundError("Site not found.")
    site.is_active = False
    record_audit(db, actor=admin, action="site.deactivated", target_type="site", target_id=site.id, ctx=ctx)
    db.flush()
    return site


def list_sites(
    db: Session,
    *,
    active_only: bool,
    search: str | None,
    campaign_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[DistributionSite], int]:
    from app.models import DistributorAssignment

    stmt = select(DistributionSite)
    if active_only:
        stmt = stmt.where(DistributionSite.is_active.is_(True))
    if search:
        stmt = stmt.where(
            DistributionSite.name.ilike(f"%{search}%") | DistributionSite.site_code.ilike(f"%{search}%")
        )
    if campaign_id:
        stmt = stmt.where(
            DistributionSite.id.in_(
                select(DistributorAssignment.site_id).where(DistributorAssignment.campaign_id == campaign_id)
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(db.scalars(stmt.order_by(DistributionSite.site_code).limit(limit).offset(offset)))
    return rows, int(total)


def get_site(db: Session, site_id: uuid.UUID) -> DistributionSite:
    site = db.get(DistributionSite, site_id)
    if site is None:
        raise NotFoundError("Site not found.")
    return site
