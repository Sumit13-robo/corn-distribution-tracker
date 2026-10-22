"""Distribution submission/review service.

State machine (docs/architecture/DOMAIN_MODEL.md):
    SUBMITTED -> APPROVED (posts exactly one DELIVERY movement, idempotent)
    SUBMITTED -> REJECTED (releases the reservation; no stock change)
    SUBMITTED -> CANCELLED (distributor before review / admin policy)
Approved records are immutable for quantity/site/distributor; corrections are new
records plus compensating movements.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.rate_limit import hit
from app.core.units import convert_to_kg
from app.models import (
    AssignmentStatus,
    DistributionRecord,
    DistributionSite,
    DistributorAssignment,
    GeoFlag,
    GeoStatus,
    MovementType,
    PhotoEvidence,
    RecordStatus,
    StockAccount,
    User,
)
from app.services import (
    evidence_service,
    inventory_service,
    settings_service,
)
from app.services.audit_service import RequestContext, record_audit
from app.services.geo_service import evaluate_geo, validate_coordinates


def submit_delivery(
    db: Session,
    *,
    user: User,
    assignment_id: uuid.UUID,
    quantity: Decimal,
    unit: str,
    notes: str | None,
    evidence_specs: list[dict[str, Any]],
    location: dict[str, Any] | None,
    idempotency_key: str,
    ctx: RequestContext,
) -> tuple[DistributionRecord, bool]:
    """Create a SUBMITTED record (a stock reservation). Returns (record, is_duplicate)."""
    allowed, retry_after = hit("deliveries.create", str(user.id))
    if not allowed:
        raise AppError(
            "Too many submissions; try again shortly.",
            code="RATE_LIMITED",
            status_code=429,
            details=[{"retry_after": retry_after}],
        )

    if not evidence_specs:
        raise AppError(
            "At least one photo is required for a delivery submission.", details=[{"field": "evidence"}]
        )

    # Idempotency: same client key returns the original record (no second reservation).
    existing = db.scalar(
        select(DistributionRecord).where(
            DistributionRecord.distributor_user_id == user.id,
            DistributionRecord.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return existing, True

    assignment = db.get(DistributorAssignment, assignment_id)
    if assignment is None or assignment.distributor_user_id != user.id:
        # 404 for foreign ids: never leak assignment existence.
        raise NotFoundError("Assignment not found.")
    if assignment.status != AssignmentStatus.ACTIVE:
        raise ConflictError("This assignment is not active.", code="ILLEGAL_STATE")
    site = db.get(DistributionSite, assignment.site_id)
    if site is None or not site.is_active:
        raise ConflictError("This site is not active.", code="ILLEGAL_STATE")

    settings_row = settings_service.get_or_create_settings(db)
    kg = convert_to_kg(quantity, unit, settings_row.kg_per_bag)

    # Reservation: lock the distributor's stock account, re-check availability.
    account = inventory_service.get_or_create_distributor_account(db, user)
    inventory_service.lock_accounts(db, account.id)
    available = inventory_service.available_kg(db, account, distributor_user_id=user.id)
    if kg > available:
        raise ConflictError(
            "This delivery would exceed your available stock (pending submissions count as reserved).",
            code="INSUFFICIENT_STOCK",
            details=[{"available_kg": str(available)}],
        )

    latitude = longitude = accuracy = None
    location_timestamp = device_time = None
    geo_result: dict[str, Any] = {
        "distance_m": None,
        "flags": [GeoFlag.GPS_MISSING.value],
        "geo_status": GeoStatus.UNAVAILABLE.value,
    }
    if location:
        lat_raw, lng_raw = location.get("latitude"), location.get("longitude")
        if lat_raw is not None and lng_raw is not None:
            latitude, longitude = validate_coordinates(Decimal(str(lat_raw)), Decimal(str(lng_raw)))
            accuracy_raw = location.get("accuracy_m")
            accuracy = Decimal(str(accuracy_raw)) if accuracy_raw is not None else None
            if accuracy is not None and accuracy < 0:
                raise AppError("Accuracy cannot be negative.", details=[{"field": "location.accuracy_m"}])
            location_timestamp = location.get("timestamp")
            device_time = location.get("device_time")
            radius = site.geofence_radius_m or settings_row.default_geofence_radius_m
            max_accuracy = site.max_acceptable_accuracy_m or settings_row.max_acceptable_gps_accuracy_m
            geo_result = evaluate_geo(
                latitude=latitude,
                longitude=longitude,
                accuracy_m=accuracy,
                location_timestamp=location_timestamp,
                site_latitude=site.latitude,
                site_longitude=site.longitude,
                geofence_radius_m=radius,
                max_accuracy_m=max_accuracy,
                max_age_seconds=settings_row.max_location_age_seconds,
            )

    record = DistributionRecord(
        campaign_id=assignment.campaign_id,
        assignment_id=assignment.id,
        site_id=site.id,
        distributor_user_id=user.id,
        quantity_kg=kg,
        status=RecordStatus.SUBMITTED,
        idempotency_key=idempotency_key,
        client_created_at=location.get("client_created_at") if location else None,
        submitted_at=datetime.now(UTC),
        notes=notes,
        location_latitude=latitude,
        location_longitude=longitude,
        location_accuracy_m=accuracy,
        location_timestamp=location_timestamp,
        device_reported_location_time=device_time,
        distance_to_site_m=Decimal(str(geo_result["distance_m"]))
        if geo_result["distance_m"] is not None
        else None,
        geo_status=GeoStatus(geo_result["geo_status"]),
        geo_flags=geo_result["flags"],
    )
    db.add(record)
    db.flush()

    evidence_service.attach_intents_to_record(
        db,
        record=record,
        user=user,
        site_latitude=site.latitude,
        site_longitude=site.longitude,
        specs=evidence_specs,
        ctx=ctx,
    )
    # Fold any evidence-level system flags into the record's flag list.
    record.geo_flags = _merge_flags(
        geo_result["flags"],
        [
            f
            for evidence_row in db.scalars(
                select(PhotoEvidence).where(PhotoEvidence.distribution_record_id == record.id)
            )
            for f in evidence_row.validation_flags
        ],
    )
    db.flush()
    record_audit(
        db,
        actor=user,
        action="distribution.submitted",
        target_type="distribution_record",
        target_id=record.id,
        details={"quantity_kg": str(kg), "geo_status": record.geo_status.value, "flags": record.geo_flags},
        ctx=ctx,
    )
    return record, False


def _merge_flags(base: list, extra: list) -> list:
    merged = list(dict.fromkeys([*base, *extra]))
    return merged


def approve_delivery(
    db: Session,
    *,
    admin: User,
    record_id: uuid.UUID,
    exception_reason: str | None,
    review_note: str | None,
    idempotency_key: str | None,
    ctx: RequestContext,
) -> tuple[DistributionRecord, bool]:
    """Approve atomically: one movement, one transition, audit event. Idempotent."""
    record = db.scalars(
        select(DistributionRecord).where(DistributionRecord.id == record_id).with_for_update()
    ).first()
    if record is None:
        raise NotFoundError("Delivery record not found.")
    if record.status == RecordStatus.APPROVED:
        return record, True  # idempotent retry: same record, no second movement
    if record.status != RecordStatus.SUBMITTED:
        raise ConflictError("Only submitted records can be approved.", code="ILLEGAL_STATE")

    site = db.get(DistributionSite, record.site_id)
    assignment = db.get(DistributorAssignment, record.assignment_id)
    assert site is not None and assignment is not None

    critical_flags = {
        GeoFlag.OUTSIDE_GEOFENCE.value,
        GeoFlag.GPS_MISSING.value,
        GeoFlag.GPS_STALE.value,
        GeoFlag.GPS_LOW_ACCURACY.value,
        GeoFlag.EXIF_GPS_MISMATCH.value,
        GeoFlag.CAPTURE_TIME_MISMATCH.value,
        GeoFlag.DUPLICATE_IMAGE_HASH.value,
    }
    evidence_rows = list(
        db.scalars(select(PhotoEvidence).where(PhotoEvidence.distribution_record_id == record.id))
    )
    flagged: set[str] = set()
    for ev in evidence_rows:
        flagged.update(ev.validation_flags or [])
    geo_critical = bool(flagged & critical_flags)
    if geo_critical and not exception_reason:
        raise ConflictError(
            "This submission has location/evidence warnings; "
            "an explicit exception reason is required to approve.",
            code="REASON_REQUIRED",
            details=[{"flags": sorted(flagged)}],
        )

    # Overage check against the assignment target.
    approved_before = db.scalar(
        select(func.coalesce(func.sum(DistributionRecord.quantity_kg), 0)).where(
            DistributionRecord.assignment_id == record.assignment_id,
            DistributionRecord.status == RecordStatus.APPROVED,
            DistributionRecord.id != record.id,
        )
    ) or Decimal(0)
    if assignment.target_quantity_kg is not None:
        projected = Decimal(approved_before) + Decimal(record.quantity_kg)
        if projected > Decimal(assignment.target_quantity_kg) and not exception_reason:
            raise ConflictError(
                "Approving this delivery exceeds the assignment target; "
                "an explicit override reason is required.",
                code="REASON_REQUIRED",
                details=[{"target_kg": str(assignment.target_quantity_kg), "projected_kg": str(projected)}],
            )

    # Transactional stock posting: lock both accounts, re-verify availability, post once.
    distributor_account = db.scalar(
        select(StockAccount).where(StockAccount.owner_user_id == record.distributor_user_id)
    )
    if distributor_account is None:
        raise ConflictError("Distributor stock account is missing.", code="ILLEGAL_STATE")
    site_account = inventory_service.get_or_create_site_account(db, record.site_id)
    inventory_service.lock_accounts(db, distributor_account.id, site_account.id)
    available = inventory_service.available_kg(
        db, distributor_account, distributor_user_id=record.distributor_user_id
    )
    if Decimal(record.quantity_kg) > available:
        raise ConflictError(
            "Stock is no longer available for this delivery "
            "(other pending submissions hold the reservation).",
            code="INSUFFICIENT_STOCK",
            details=[{"available_kg": str(available)}],
        )

    movement = inventory_service.post_movement(
        db,
        movement_type=MovementType.DELIVERY,
        source_account_id=distributor_account.id,
        destination_account_id=site_account.id,
        quantity_kg=Decimal(record.quantity_kg),
        reference_type="distribution_record",
        reference_id=record.id,
        distribution_reference_id=record.id,  # unique index: hard idempotency guard
        idempotency_key=idempotency_key,
        created_by=admin.id,
        reason=review_note,
        metadata={
            "assignment_id": str(record.assignment_id),
            "campaign_id": str(record.campaign_id) if record.campaign_id else None,
        },
    )
    record.stock_movement_id = movement.id
    record.status = RecordStatus.APPROVED
    record.reviewed_at = datetime.now(UTC)
    record.reviewed_by = admin.id
    record.review_reason = review_note
    if exception_reason:
        record.review_exception_reason = exception_reason
        if GeoFlag.LOCATION_EXCEPTION.value not in record.geo_flags:
            record.geo_flags = list(record.geo_flags) + [GeoFlag.LOCATION_EXCEPTION.value]
    record_audit(
        db,
        actor=admin,
        action="distribution.approved",
        target_type="distribution_record",
        target_id=record.id,
        reason=exception_reason or review_note,
        details={"quantity_kg": str(record.quantity_kg), "stock_movement_id": str(movement.id)},
        ctx=ctx,
    )
    db.flush()
    return record, False


def reject_delivery(
    db: Session, *, admin: User, record_id: uuid.UUID, reason: str, ctx: RequestContext
) -> tuple[DistributionRecord, bool]:
    if not reason or not reason.strip():
        raise AppError("A rejection reason is required.", details=[{"field": "reason"}])
    record = db.scalars(
        select(DistributionRecord).where(DistributionRecord.id == record_id).with_for_update()
    ).first()
    if record is None:
        raise NotFoundError("Delivery record not found.")
    if record.status == RecordStatus.REJECTED:
        return record, True
    if record.status != RecordStatus.SUBMITTED:
        raise ConflictError("Only submitted records can be rejected.", code="ILLEGAL_STATE")
    record.status = RecordStatus.REJECTED
    record.reviewed_at = datetime.now(UTC)
    record.reviewed_by = admin.id
    record.review_reason = reason
    record_audit(
        db,
        actor=admin,
        action="distribution.rejected",
        target_type="distribution_record",
        target_id=record.id,
        reason=reason,
        ctx=ctx,
    )
    db.flush()
    return record, False


def cancel_delivery(
    db: Session, *, actor: User, record_id: uuid.UUID, reason: str | None, ctx: RequestContext
) -> tuple[DistributionRecord, bool]:
    record = db.scalars(
        select(DistributionRecord).where(DistributionRecord.id == record_id).with_for_update()
    ).first()
    if record is None:
        raise NotFoundError("Delivery record not found.")
    if actor.role != "ADMIN" and record.distributor_user_id != actor.id:
        raise NotFoundError("Delivery record not found.")
    if record.status == RecordStatus.CANCELLED:
        return record, True
    if record.status not in (RecordStatus.SUBMITTED, RecordStatus.DRAFT):
        raise ConflictError(
            "Only pending records can be cancelled; posted corrections use a reversal.", code="ILLEGAL_STATE"
        )
    record.status = RecordStatus.CANCELLED
    record.reviewed_at = datetime.now(UTC)
    record.reviewed_by = actor.id
    record.review_reason = reason
    record_audit(
        db,
        actor=actor,
        action="distribution.cancelled",
        target_type="distribution_record",
        target_id=record.id,
        reason=reason,
        ctx=ctx,
    )
    db.flush()
    return record, False


# ---------------------------------------------------------------------------
# Scoped reads
# ---------------------------------------------------------------------------


def scope_records_query(
    db: Session,
    *,
    user: User,
    status: RecordStatus | None,
    campaign_id: uuid.UUID | None,
    site_id: uuid.UUID | None,
    distributor_user_id: uuid.UUID | None,
    from_ts: datetime | None,
    to_ts: datetime | None,
):
    stmt = select(DistributionRecord)
    if user.role != "ADMIN":
        stmt = stmt.where(DistributionRecord.distributor_user_id == user.id)
    else:
        if distributor_user_id:
            stmt = stmt.where(DistributionRecord.distributor_user_id == distributor_user_id)
    if status:
        stmt = stmt.where(DistributionRecord.status == status)
    if campaign_id:
        stmt = stmt.where(DistributionRecord.campaign_id == campaign_id)
    if site_id:
        stmt = stmt.where(DistributionRecord.site_id == site_id)
    if from_ts:
        stmt = stmt.where(DistributionRecord.submitted_at >= from_ts)
    if to_ts:
        stmt = stmt.where(DistributionRecord.submitted_at <= to_ts)
    return stmt


def get_record_scoped(db: Session, *, user: User, record_id: uuid.UUID) -> DistributionRecord:
    record = db.get(DistributionRecord, record_id)
    if record is None:
        raise NotFoundError("Delivery record not found.")
    if user.role != "ADMIN" and record.distributor_user_id != user.id:
        raise NotFoundError("Delivery record not found.")
    return record


def assignment_progress(
    db: Session, *, assignment_ids: list[uuid.UUID]
) -> dict[uuid.UUID, dict[str, Decimal]]:
    """Per-assignment approved/pending sums from records (explicit denominators)."""
    if not assignment_ids:
        return {}
    rows = db.execute(
        select(
            DistributionRecord.assignment_id,
            DistributionRecord.status,
            func.coalesce(func.sum(DistributionRecord.quantity_kg), 0),
        )
        .where(DistributionRecord.assignment_id.in_(assignment_ids))
        .group_by(DistributionRecord.assignment_id, DistributionRecord.status)
    ).all()
    result: dict[uuid.UUID, dict[str, Decimal]] = {}
    for assignment_id, status, total in rows:
        bucket = result.setdefault(
            assignment_id, {"approved_kg": Decimal(0), "pending_kg": Decimal(0), "rejected_kg": Decimal(0)}
        )
        if status == RecordStatus.APPROVED:
            bucket["approved_kg"] = Decimal(total)
        elif status == RecordStatus.SUBMITTED:
            bucket["pending_kg"] = Decimal(total)
        elif status == RecordStatus.REJECTED:
            bucket["rejected_kg"] = Decimal(total)
    return result


def last_visit_at(db: Session, *, site_id: uuid.UUID) -> datetime | None:
    return db.scalar(
        select(func.max(DistributionRecord.submitted_at)).where(DistributionRecord.site_id == site_id)
    )
