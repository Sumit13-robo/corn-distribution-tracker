"""Analytics service. Formulas are canonical per docs/architecture/INVENTORY_LEDGER.md.

Careful: pending submissions are reservations - they are never counted as approved
delivery. Remaining target floors at zero and overage is reported separately.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AccountType,
    DistributionRecord,
    DistributionSite,
    DistributorAssignment,
    MovementType,
    PhotoEvidence,
    RecordStatus,
    StockAccount,
    StockMovement,
    User,
)
from app.services.inventory_service import posted_balance_kg, reserved_kg

_CRITICAL_EVIDENCE_FLAGS = {
    "UNEXPECTED_FILE_TYPE",
    "CAPTURE_TIME_MISMATCH",
    "EXIF_GPS_MISMATCH",
    "DUPLICATE_IMAGE_HASH",
}
_GEO_CRITICAL_FLAGS = {
    "GPS_MISSING",
    "GPS_STALE",
    "GPS_LOW_ACCURACY",
    "OUTSIDE_GEOFENCE",
}


def _records_query(
    db: Session,
    *,
    scope_user: User | None,
    campaign_id: uuid.UUID | None,
    from_ts: datetime | None,
    to_ts: datetime | None,
):
    stmt = select(DistributionRecord)
    if scope_user is not None:
        stmt = stmt.where(DistributionRecord.distributor_user_id == scope_user.id)
    if campaign_id:
        stmt = stmt.where(DistributionRecord.campaign_id == campaign_id)
    if from_ts:
        stmt = stmt.where(DistributionRecord.submitted_at >= from_ts)
    if to_ts:
        stmt = stmt.where(DistributionRecord.submitted_at <= to_ts)
    return stmt


def _movement_sum(
    db: Session,
    *,
    movement_type: MovementType,
    destination_account_id: uuid.UUID | None = None,
    source_account_id: uuid.UUID | None = None,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
) -> Decimal:
    stmt = select(func.coalesce(func.sum(StockMovement.quantity_kg), 0)).where(
        StockMovement.movement_type == movement_type
    )
    if destination_account_id is not None:
        stmt = stmt.where(StockMovement.destination_account_id == destination_account_id)
    if source_account_id is not None:
        stmt = stmt.where(StockMovement.source_account_id == source_account_id)
    if from_ts:
        stmt = stmt.where(StockMovement.posted_at >= from_ts)
    if to_ts:
        stmt = stmt.where(StockMovement.posted_at <= to_ts)
    return Decimal(db.scalar(stmt) or 0)


def overview(
    db: Session,
    *,
    scope_user: User | None,
    campaign_id: uuid.UUID | None,
    from_ts: datetime | None,
    to_ts: datetime | None,
) -> dict[str, Any]:
    records_stmt = _records_query(
        db, scope_user=scope_user, campaign_id=campaign_id, from_ts=from_ts, to_ts=to_ts
    )
    records = list(db.scalars(records_stmt))

    submitted_pending = sum(
        (Decimal(r.quantity_kg) for r in records if r.status == RecordStatus.SUBMITTED), Decimal(0)
    )
    approved_delivered = sum(
        (Decimal(r.quantity_kg) for r in records if r.status == RecordStatus.APPROVED), Decimal(0)
    )
    rejected_kg = sum(
        (Decimal(r.quantity_kg) for r in records if r.status == RecordStatus.REJECTED), Decimal(0)
    )
    open_review = sum(1 for r in records if r.status == RecordStatus.SUBMITTED)

    assignment_ids = list({r.assignment_id for r in records})
    targets = Decimal(0)
    remaining = Decimal(0)
    overage = Decimal(0)
    if assignment_ids:
        assignments = {
            a.id: a
            for a in db.scalars(
                select(DistributorAssignment).where(DistributorAssignment.id.in_(assignment_ids))
            )
        }
        approved_by_assignment: dict[uuid.UUID, Decimal] = {}
        for r in records:
            if r.status == RecordStatus.APPROVED:
                approved_by_assignment[r.assignment_id] = approved_by_assignment.get(
                    r.assignment_id, Decimal(0)
                ) + Decimal(r.quantity_kg)
        for a_id, a in assignments.items():
            targets += Decimal(a.target_quantity_kg)
            approved_for = approved_by_assignment.get(a_id, Decimal(0))
            remaining += max(Decimal(a.target_quantity_kg) - approved_for, Decimal(0))
            overage += max(approved_for - Decimal(a.target_quantity_kg), Decimal(0))

    # Evidence completeness: approved records with at least one evidence item.
    approved_records = [r for r in records if r.status == RecordStatus.APPROVED]
    approved_ids = [r.id for r in approved_records]
    evidence_counts: dict[uuid.UUID, int] = {}
    flagged_record_ids: set[uuid.UUID] = set()
    if approved_ids:
        for ev in db.scalars(
            select(PhotoEvidence).where(PhotoEvidence.distribution_record_id.in_(approved_ids))
        ):
            owner_id = ev.distribution_record_id
            if owner_id is None:  # unattached evidence is not part of this scope
                continue
            evidence_counts[owner_id] = evidence_counts.get(owner_id, 0) + 1
            if set(ev.validation_flags or []) & _CRITICAL_EVIDENCE_FLAGS:
                flagged_record_ids.add(owner_id)
    flagged_geo_count = sum(1 for r in records if set(r.geo_flags or []) & _GEO_CRITICAL_FLAGS)
    with_evidence = sum(1 for r in approved_records if evidence_counts.get(r.id, 0) > 0)

    stock = account_stock(db, scope_user=scope_user)

    return {
        "filters": {"campaign_id": campaign_id, "from": from_ts, "to": to_ts},
        "stock": stock,
        "submitted_pending_kg": submitted_pending,
        "approved_delivered_kg": approved_delivered,
        "rejected_kg": rejected_kg,
        "open_review_count": open_review,
        "target_kg": targets,
        "remaining_target_kg": remaining,
        "over_target_kg": overage,
        "evidence_completeness": {
            "approved_with_evidence": with_evidence,
            "approved_total": len(approved_records),
            "ratio": (with_evidence / len(approved_records)) if approved_records else None,
        },
        "flagged_record_count": len(flagged_record_ids) + flagged_geo_count,
        "unit": "kg",
    }


def account_stock(db: Session, *, scope_user: User | None) -> dict[str, Any]:
    """Ledger-derived stock positions."""
    accounts = list(db.scalars(select(StockAccount).order_by(StockAccount.account_type)))
    result: dict[str, Decimal] = {
        "central_on_hand_kg": Decimal(0),
        "distributor_held_kg": Decimal(0),
        "site_stock_kg": Decimal(0),
    }
    reserved_total = Decimal(0)
    for account in accounts:
        balance = posted_balance_kg(db, account.id)
        if account.account_type == AccountType.CENTRAL:
            if scope_user is None:
                result["central_on_hand_kg"] += balance
        elif account.account_type == AccountType.DISTRIBUTOR:
            if scope_user is None or account.owner_user_id == scope_user.id:
                balance = posted_balance_kg(db, account.id)
                result["distributor_held_kg"] += balance
                if account.owner_user_id:
                    reserved_total += reserved_kg(db, account.owner_user_id)
        elif account.account_type == AccountType.SITE:
            result["site_stock_kg"] += balance
    result["reserved_pending_kg"] = reserved_total
    return result


def distributor_performance(
    db: Session, *, campaign_id: uuid.UUID | None, from_ts: datetime | None, to_ts: datetime | None
) -> list[dict[str, Any]]:
    distributors = list(
        db.scalars(select(User).where(User.role == "DISTRIBUTOR").order_by(User.display_name))
    )
    out: list[dict[str, Any]] = []
    for distributor in distributors:
        stmt = select(DistributionRecord).where(DistributionRecord.distributor_user_id == distributor.id)
        if campaign_id:
            stmt = stmt.where(DistributionRecord.campaign_id == campaign_id)
        if from_ts:
            stmt = stmt.where(DistributionRecord.submitted_at >= from_ts)
        if to_ts:
            stmt = stmt.where(DistributionRecord.submitted_at <= to_ts)
        records = list(db.scalars(stmt))
        target = db.scalar(
            select(func.coalesce(func.sum(DistributorAssignment.target_quantity_kg), 0)).where(
                DistributorAssignment.distributor_user_id == distributor.id,
                DistributorAssignment.status.in_(["ACTIVE", "PAUSED"]),
                *([DistributorAssignment.campaign_id == campaign_id] if campaign_id else []),
            )
        ) or Decimal(0)
        approved = sum(
            (Decimal(r.quantity_kg) for r in records if r.status == RecordStatus.APPROVED), Decimal(0)
        )
        pending = sum(
            (Decimal(r.quantity_kg) for r in records if r.status == RecordStatus.SUBMITTED), Decimal(0)
        )
        rejected = sum(
            (Decimal(r.quantity_kg) for r in records if r.status == RecordStatus.REJECTED), Decimal(0)
        )
        flagged = sum(1 for r in records if set(r.geo_flags or []) & _GEO_CRITICAL_FLAGS)
        exceptions = sum(
            1 for r in records if r.status == RecordStatus.APPROVED and r.review_exception_reason
        )
        account = db.scalar(select(StockAccount).where(StockAccount.owner_user_id == distributor.id))
        balance = posted_balance_kg(db, account.id) if account else Decimal(0)
        out.append(
            {
                "distributor_user_id": distributor.id,
                "display_name": distributor.display_name,
                "email": distributor.email_normalized,
                "is_active": distributor.is_active,
                "target_kg": Decimal(target),
                "submitted_kg": approved + pending + rejected,
                "approved_kg": approved,
                "pending_kg": pending,
                "rejected_kg": rejected,
                "remaining_target_kg": max(Decimal(target) - approved, Decimal(0)),
                "over_target_kg": max(approved - Decimal(target), Decimal(0)),
                "stock_balance_kg": balance,
                "flagged_submissions": flagged,
                "approved_with_exception": exceptions,
                "denominator_note": "submitted_kg = approved + pending + rejected within the selected window",
            }
        )
    return out


def site_performance(
    db: Session, *, campaign_id: uuid.UUID | None, from_ts: datetime | None, to_ts: datetime | None
) -> list[dict[str, Any]]:
    sites = list(db.scalars(select(DistributionSite).order_by(DistributionSite.site_code)))
    out = []
    for site in sites:
        stmt = select(DistributionRecord).where(DistributionRecord.site_id == site.id)
        if campaign_id:
            stmt = stmt.where(DistributionRecord.campaign_id == campaign_id)
        if from_ts:
            stmt = stmt.where(DistributionRecord.submitted_at >= from_ts)
        if to_ts:
            stmt = stmt.where(DistributionRecord.submitted_at <= to_ts)
        records = list(db.scalars(stmt))
        target = db.scalar(
            select(func.coalesce(func.sum(DistributorAssignment.target_quantity_kg), 0)).where(
                DistributorAssignment.site_id == site.id,
                DistributorAssignment.status.in_(["ACTIVE", "PAUSED"]),
                *([DistributorAssignment.campaign_id == campaign_id] if campaign_id else []),
            )
        ) or Decimal(0)
        approved = sum(
            (Decimal(r.quantity_kg) for r in records if r.status == RecordStatus.APPROVED), Decimal(0)
        )
        pending = sum(
            (Decimal(r.quantity_kg) for r in records if r.status == RecordStatus.SUBMITTED), Decimal(0)
        )
        rejected = sum(
            (Decimal(r.quantity_kg) for r in records if r.status == RecordStatus.REJECTED), Decimal(0)
        )
        record_ids = [r.id for r in records]
        evidence_status = "NONE"
        if record_ids:
            count = (
                db.scalar(
                    select(func.count())
                    .select_from(PhotoEvidence)
                    .where(PhotoEvidence.distribution_record_id.in_(record_ids))
                )
                or 0
            )
            evidence_status = "EVIDENCE_PRESENT" if int(count) > 0 else "EVIDENCE_MISSING"
        last_visit = db.scalar(
            select(func.max(DistributionRecord.submitted_at)).where(DistributionRecord.site_id == site.id)
        )
        out.append(
            {
                "site_id": site.id,
                "site_code": site.site_code,
                "site_name": site.name,
                "is_active": site.is_active,
                "target_kg": Decimal(target),
                "approved_kg": approved,
                "pending_kg": pending,
                "rejected_kg": rejected,
                "remaining_target_kg": max(Decimal(target) - approved, Decimal(0)),
                "last_visit_at": last_visit,
                "evidence_status": evidence_status,
                "denominator_note": (
                    "target basis: sum of open assignment targets for this site in the selected campaign"
                ),
            }
        )
    return out


def map_sites(
    db: Session,
    *,
    bbox: tuple[float, float, float, float] | None,
    campaign_id: uuid.UUID | None,
    distributor_user_id: uuid.UUID | None,
) -> list[dict[str, Any]]:
    """Map features: coordinates + per-site aggregate summaries (no private URLs)."""
    stmt = select(DistributionSite).order_by(DistributionSite.site_code)
    if bbox is not None:
        min_lng, min_lat, max_lng, max_lat = bbox
        stmt = stmt.where(
            DistributionSite.latitude >= Decimal(str(min_lat)),
            DistributionSite.latitude <= Decimal(str(max_lat)),
            DistributionSite.longitude >= Decimal(str(min_lng)),
            DistributionSite.longitude <= Decimal(str(max_lng)),
        )
    sites = list(db.scalars(stmt))
    out = []
    for site in sites:
        rec_stmt = select(DistributionRecord).where(DistributionRecord.site_id == site.id)
        if campaign_id:
            rec_stmt = rec_stmt.where(DistributionRecord.campaign_id == campaign_id)
        if distributor_user_id:
            rec_stmt = rec_stmt.where(DistributionRecord.distributor_user_id == distributor_user_id)
        records = list(db.scalars(rec_stmt))
        target = db.scalar(
            select(func.coalesce(func.sum(DistributorAssignment.target_quantity_kg), 0)).where(
                DistributorAssignment.site_id == site.id,
                DistributorAssignment.status.in_(["ACTIVE", "PAUSED"]),
                *([DistributorAssignment.campaign_id == campaign_id] if campaign_id else []),
            )
        ) or Decimal(0)
        approved = sum(
            (Decimal(r.quantity_kg) for r in records if r.status == RecordStatus.APPROVED), Decimal(0)
        )
        pending = sum(
            (Decimal(r.quantity_kg) for r in records if r.status == RecordStatus.SUBMITTED), Decimal(0)
        )
        remaining = max(Decimal(target) - approved, Decimal(0))
        if approved > 0 and pending == 0 and remaining == 0:
            status = "COMPLETE"
        elif pending > 0:
            status = "PENDING"
        elif approved > 0:
            status = "IN_PROGRESS"
        else:
            status = "NO_ACTIVITY"
        last_visit = db.scalar(
            select(func.max(DistributionRecord.submitted_at)).where(DistributionRecord.site_id == site.id)
        )
        flagged = any(set(r.geo_flags or []) & _GEO_CRITICAL_FLAGS for r in records)
        out.append(
            {
                "id": site.id,
                "site_code": site.site_code,
                "name": site.name,
                "latitude": site.latitude,
                "longitude": site.longitude,
                "is_active": site.is_active,
                "target_kg": Decimal(target),
                "approved_kg": approved,
                "pending_kg": pending,
                "remaining_target_kg": remaining,
                "submission_count": len(records),
                "status": status,
                "last_visit_at": last_visit,
                "has_flagged_evidence": flagged,
            }
        )
    return out
