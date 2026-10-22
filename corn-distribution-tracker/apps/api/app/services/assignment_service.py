"""Assignment domain service: distributor + campaign + site + target (kg)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.units import convert_to_kg
from app.models import AssignmentStatus, DistributionSite, DistributorAssignment, User
from app.services import settings_service
from app.services.audit_service import RequestContext, record_audit


def create_assignment(db: Session, *, admin: User, data: dict, ctx: RequestContext) -> DistributorAssignment:
    site = db.get(DistributionSite, data["site_id"])
    if site is None or not site.is_active:
        raise NotFoundError("Site not found or inactive.")
    distributor = db.get(User, data["distributor_user_id"])
    if distributor is None or distributor.role != "DISTRIBUTOR" or not distributor.is_active:
        raise NotFoundError("Distributor not found.")
    settings_row = settings_service.get_or_create_settings(db)
    kg = convert_to_kg(Decimal(str(data["target_quantity"])), data.get("unit", "KG"), settings_row.kg_per_bag)
    # Open-assignment uniqueness is enforced by a partial unique index; surface it nicely.
    open_conflict = db.scalar(
        select(DistributorAssignment).where(
            DistributorAssignment.campaign_id == data.get("campaign_id"),
            DistributorAssignment.site_id == data["site_id"],
            DistributorAssignment.distributor_user_id == data["distributor_user_id"],
            DistributorAssignment.status.in_([AssignmentStatus.ACTIVE, AssignmentStatus.PAUSED]),
        )
    )
    if open_conflict is not None:
        raise ConflictError(
            "An open assignment already exists for this distributor, campaign and site.", code="DUPLICATE"
        )
    assignment = DistributorAssignment(
        campaign_id=data.get("campaign_id"),
        site_id=data["site_id"],
        distributor_user_id=data["distributor_user_id"],
        target_quantity_kg=kg,
        due_at=data.get("due_at"),
        status=AssignmentStatus.ACTIVE,
        notes=data.get("notes"),
        created_by=admin.id,
    )
    db.add(assignment)
    record_audit(
        db,
        actor=admin,
        action="assignment.created",
        target_type="assignment",
        target_id=assignment.id,
        details={"target_kg": str(kg), "site_id": str(site.id), "distributor_user_id": str(distributor.id)},
        ctx=ctx,
    )
    db.flush()
    return assignment


def update_assignment(
    db: Session, *, admin: User, assignment_id: uuid.UUID, data: dict, ctx: RequestContext
) -> DistributorAssignment:
    assignment = db.get(DistributorAssignment, assignment_id)
    if assignment is None:
        raise NotFoundError("Assignment not found.")
    for key in ("due_at", "status", "notes"):
        if key in data:
            setattr(assignment, key, data[key])
    if "target_quantity" in data:
        settings_row = settings_service.get_or_create_settings(db)
        kg = convert_to_kg(
            Decimal(str(data["target_quantity"])), data.get("unit", "KG"), settings_row.kg_per_bag
        )
        assignment.target_quantity_kg = kg
    record_audit(
        db,
        actor=admin,
        action="assignment.updated",
        target_type="assignment",
        target_id=assignment.id,
        details={"changed_fields": list(data.keys())},
        ctx=ctx,
    )
    db.flush()
    return assignment


def get_assignment_scoped(db: Session, *, user: User, assignment_id: uuid.UUID) -> DistributorAssignment:
    assignment = db.get(DistributorAssignment, assignment_id)
    if assignment is None:
        raise NotFoundError("Assignment not found.")
    if user.role != "ADMIN" and assignment.distributor_user_id != user.id:
        raise NotFoundError("Assignment not found.")
    return assignment


def list_assignments(
    db: Session, *, user: User, campaign_id: uuid.UUID | None, limit: int, offset: int
) -> tuple[list[DistributorAssignment], int]:
    stmt = select(DistributorAssignment)
    if user.role != "ADMIN":
        stmt = stmt.where(DistributorAssignment.distributor_user_id == user.id)
    if campaign_id:
        stmt = stmt.where(DistributorAssignment.campaign_id == campaign_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(stmt.order_by(DistributorAssignment.created_at.desc()).limit(limit).offset(offset))
    )
    return rows, int(total)


def distributor_me_assignments(db: Session, *, user: User) -> list[dict]:
    """Distributor self-service list with site details and progress aggregates."""
    if user.role == "ADMIN":
        raise AppError("This endpoint is for distributors.", status_code=403)
    from app.services.distribution_service import assignment_progress

    rows = list(
        db.scalars(
            select(DistributorAssignment)
            .where(DistributorAssignment.distributor_user_id == user.id)
            .order_by(DistributorAssignment.created_at.desc())
        )
    )
    progress = assignment_progress(db, assignment_ids=[a.id for a in rows])
    sites = {
        s.id: s
        for s in db.scalars(
            select(DistributionSite).where(
                DistributionSite.id.in_({a.site_id for a in rows} or {uuid.uuid4()})
            )
        )
    }
    result = []
    for assignment in rows:
        site = sites.get(assignment.site_id)
        agg = progress.get(
            assignment.id, {"approved_kg": Decimal(0), "pending_kg": Decimal(0), "rejected_kg": Decimal(0)}
        )
        target = Decimal(assignment.target_quantity_kg)
        approved = Decimal(agg["approved_kg"])
        result.append(
            {
                "assignment_id": assignment.id,
                "campaign_id": assignment.campaign_id,
                "due_at": assignment.due_at,
                "status": assignment.status.value,
                "target_kg": target,
                "approved_kg": approved,
                "pending_kg": Decimal(agg["pending_kg"]),
                "remaining_target_kg": max(target - approved, Decimal(0)),
                "over_target_kg": max(approved - target, Decimal(0)),
                "site": {
                    "id": site.id,
                    "site_code": site.site_code,
                    "name": site.name,
                    "address_text": site.address_text,
                    "latitude": site.latitude,
                    "longitude": site.longitude,
                    "geofence_radius_m": site.geofence_radius_m,
                    "max_acceptable_accuracy_m": site.max_acceptable_accuracy_m,
                }
                if site
                else None,
            }
        )
    return result
