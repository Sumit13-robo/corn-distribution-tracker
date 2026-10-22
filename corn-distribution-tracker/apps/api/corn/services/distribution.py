"""Distribution submission, review and scoped reads."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.db.models import QuerySet, Sum
from django.utils import timezone

from ..enums import AssignmentStatus, GeoFlag, GeoStatus, MovementType, RecordStatus
from ..errors import AppError, ConflictError, NotFoundError, RateLimitedError
from ..geo import evaluate_geo, validate_coordinates
from ..models import (
    DistributionRecord,
    DistributionSite,
    DistributorAssignment,
    PhotoEvidence,
    StockAccount,
    User,
)
from ..rate_limit import hit
from ..units import convert_to_kg
from . import evidence as evidence_service
from . import inventory as inventory_service
from . import settings as settings_service_
from .audit import RequestContext, record_audit

ZERO = Decimal("0")


def _merge_flags(base: list, extra: list) -> list:
    return list(dict.fromkeys([*base, *extra]))


def submit_delivery(
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
    allowed, retry_after = hit("deliveries.create", str(user.id))
    if not allowed:
        raise RateLimitedError(retry_after=retry_after)

    if not evidence_specs:
        raise AppError(
            "At least one photo is required for a delivery submission.",
            details=[{"field": "evidence"}],
        )
    existing = DistributionRecord.objects.filter(
        distributor_user_id=user.id, idempotency_key=idempotency_key
    ).first()
    if existing is not None:
        return existing, True

    assignment = DistributorAssignment.objects.filter(id=assignment_id).first()
    if assignment is None or assignment.distributor_user_id != user.id:
        raise NotFoundError("Assignment not found.")
    if assignment.status != AssignmentStatus.ACTIVE:
        raise ConflictError("This assignment is not active.", code="ILLEGAL_STATE")
    site = DistributionSite.objects.filter(id=assignment.site_id).first()
    if site is None or not site.is_active:
        raise ConflictError("This site is not active.", code="ILLEGAL_STATE")

    settings_row = settings_service_.get_or_create_settings()
    kg = convert_to_kg(quantity, unit, settings_row.kg_per_bag)

    account = inventory_service.get_or_create_distributor_account(user)
    inventory_service.lock_accounts(account.id)
    available = inventory_service.available_kg(account, distributor_user_id=user.id)
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
            max_accuracy = (
                site.max_acceptable_accuracy_m or settings_row.max_acceptable_gps_accuracy_m
            )
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

    record = DistributionRecord.objects.create(
        campaign=assignment.campaign,
        assignment=assignment,
        site=site,
        distributor_user=user,
        quantity_kg=kg,
        status=RecordStatus.SUBMITTED,
        idempotency_key=idempotency_key,
        client_created_at=location.get("client_created_at") if location else None,
        submitted_at=timezone.now(),
        notes=notes,
        location_latitude=latitude,
        location_longitude=longitude,
        location_accuracy_m=accuracy,
        location_timestamp=location_timestamp,
        device_reported_location_time=device_time,
        distance_to_site_m=(
            Decimal(str(geo_result["distance_m"])) if geo_result["distance_m"] is not None else None
        ),
        geo_status=GeoStatus(geo_result["geo_status"]),
        geo_flags=geo_result["flags"],
    )

    evidence_service.attach_intents_to_record(
        record=record,
        user=user,
        site_latitude=site.latitude,
        site_longitude=site.longitude,
        specs=evidence_specs,
        ctx=ctx,
    )
    record.geo_flags = _merge_flags(
        geo_result["flags"],
        [
            flag
            for evidence_row in PhotoEvidence.objects.filter(distribution_record=record)
            for flag in (evidence_row.validation_flags or [])
        ],
    )
    record.save(update_fields=["geo_flags", "updated_at"])
    record_audit(
        actor=user,
        action="distribution.submitted",
        target_type="distribution_record",
        target_id=record.id,
        details={
            "quantity_kg": str(kg),
            "geo_status": record.geo_status,
            "flags": record.geo_flags,
        },
        ctx=ctx,
    )
    return record, False


def approve_delivery(
    *,
    admin: User,
    record_id: uuid.UUID,
    exception_reason: str | None,
    review_note: str | None,
    idempotency_key: str | None,
    ctx: RequestContext,
) -> tuple[DistributionRecord, bool]:
    record = (
        DistributionRecord.objects.select_for_update().filter(id=record_id).first()
    )
    if record is None:
        raise NotFoundError("Delivery record not found.")
    if record.status == RecordStatus.APPROVED:
        return record, True
    if record.status != RecordStatus.SUBMITTED:
        raise ConflictError("Only submitted records can be approved.", code="ILLEGAL_STATE")

    site = DistributionSite.objects.filter(id=record.site_id).first()
    assignment = DistributorAssignment.objects.filter(id=record.assignment_id).first()
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
    evidence_rows = PhotoEvidence.objects.filter(distribution_record=record)
    flagged: set[str] = set(record.geo_flags or [])
    for item in evidence_rows:
        flagged.update(item.validation_flags or [])
    if flagged & critical_flags and not exception_reason:
        raise ConflictError(
            "This submission has location/evidence warnings; "
            "an explicit exception reason is required to approve.",
            code="REASON_REQUIRED",
            details=[{"flags": sorted(flagged)}],
        )

    approved_before = (
        DistributionRecord.objects.filter(
            assignment_id=record.assignment_id,
            status=RecordStatus.APPROVED,
        )
        .exclude(id=record.id)
        .aggregate(total=Sum("quantity_kg"))["total"]
        or ZERO
    )
    if assignment.target_quantity_kg is not None:
        projected = Decimal(approved_before) + Decimal(record.quantity_kg)
        if projected > Decimal(assignment.target_quantity_kg) and not exception_reason:
            raise ConflictError(
                "Approving this delivery exceeds the assignment target; "
                "an explicit override reason is required.",
                code="REASON_REQUIRED",
                details=[
                    {"target_kg": str(assignment.target_quantity_kg), "projected_kg": str(projected)}
                ],
            )

    distributor_account = StockAccount.objects.filter(owner_user_id=record.distributor_user_id).first()
    if distributor_account is None:
        raise ConflictError("Distributor stock account is missing.", code="ILLEGAL_STATE")
    site_account = inventory_service.get_or_create_site_account(record.site_id)
    inventory_service.lock_accounts(distributor_account.id, site_account.id)
    available = inventory_service.available_kg(
        distributor_account, distributor_user_id=record.distributor_user_id
    )
    if Decimal(record.quantity_kg) > available:
        raise ConflictError(
            "Stock is no longer available for this delivery "
            "(other pending submissions hold the reservation).",
            code="INSUFFICIENT_STOCK",
            details=[{"available_kg": str(available)}],
        )

    movement = inventory_service.post_movement(
        movement_type=MovementType.DELIVERY,
        source_account_id=distributor_account.id,
        destination_account_id=site_account.id,
        quantity_kg=Decimal(record.quantity_kg),
        reference_type="distribution_record",
        reference_id=record.id,
        distribution_reference_id=record.id,
        idempotency_key=idempotency_key,
        created_by=admin.id,
        reason=review_note,
        metadata={
            "assignment_id": str(record.assignment_id),
            "campaign_id": str(record.campaign_id) if record.campaign_id else None,
        },
    )
    record.stock_movement = movement
    record.status = RecordStatus.APPROVED
    record.reviewed_at = timezone.now()
    record.reviewed_by = admin
    record.review_reason = review_note
    if exception_reason:
        record.review_exception_reason = exception_reason
        if GeoFlag.LOCATION_EXCEPTION.value not in (record.geo_flags or []):
            record.geo_flags = list(record.geo_flags or []) + [GeoFlag.LOCATION_EXCEPTION.value]
    record.save()
    record_audit(
        actor=admin,
        action="distribution.approved",
        target_type="distribution_record",
        target_id=record.id,
        reason=exception_reason or review_note,
        details={"quantity_kg": str(record.quantity_kg), "stock_movement_id": str(movement.id)},
        ctx=ctx,
    )
    return record, False


def reject_delivery(
    *, admin: User, record_id: uuid.UUID, reason: str, ctx: RequestContext
) -> tuple[DistributionRecord, bool]:
    if not reason or not reason.strip():
        raise AppError("A rejection reason is required.", details=[{"field": "reason"}])
    record = DistributionRecord.objects.select_for_update().filter(id=record_id).first()
    if record is None:
        raise NotFoundError("Delivery record not found.")
    if record.status == RecordStatus.REJECTED:
        return record, True
    if record.status != RecordStatus.SUBMITTED:
        raise ConflictError("Only submitted records can be rejected.", code="ILLEGAL_STATE")
    record.status = RecordStatus.REJECTED
    record.reviewed_at = timezone.now()
    record.reviewed_by = admin
    record.review_reason = reason
    record.save()
    record_audit(
        actor=admin,
        action="distribution.rejected",
        target_type="distribution_record",
        target_id=record.id,
        reason=reason,
        ctx=ctx,
    )
    return record, False


def cancel_delivery(
    *, actor: User, record_id: uuid.UUID, reason: str | None, ctx: RequestContext
) -> tuple[DistributionRecord, bool]:
    record = DistributionRecord.objects.select_for_update().filter(id=record_id).first()
    if record is None:
        raise NotFoundError("Delivery record not found.")
    if actor.role != "ADMIN" and record.distributor_user_id != actor.id:
        raise NotFoundError("Delivery record not found.")
    if record.status == RecordStatus.CANCELLED:
        return record, True
    if record.status not in (RecordStatus.SUBMITTED, RecordStatus.DRAFT):
        raise ConflictError(
            "Only pending records can be cancelled; posted corrections use a reversal.",
            code="ILLEGAL_STATE",
        )
    record.status = RecordStatus.CANCELLED
    record.reviewed_at = timezone.now()
    record.reviewed_by = actor
    record.review_reason = reason
    record.save()
    record_audit(
        actor=actor,
        action="distribution.cancelled",
        target_type="distribution_record",
        target_id=record.id,
        reason=reason,
        ctx=ctx,
    )
    return record, False


def scope_records_query(
    *,
    user: User,
    status: str | None,
    campaign_id: uuid.UUID | None,
    site_id: uuid.UUID | None,
    distributor_user_id: uuid.UUID | None,
    from_ts: datetime | None,
    to_ts: datetime | None,
) -> QuerySet[DistributionRecord]:
    qs = DistributionRecord.objects.select_related("site", "distributor_user").all()
    if user.role != "ADMIN":
        qs = qs.filter(distributor_user_id=user.id)
    elif distributor_user_id:
        qs = qs.filter(distributor_user_id=distributor_user_id)
    if status:
        qs = qs.filter(status=status)
    if campaign_id:
        qs = qs.filter(campaign_id=campaign_id)
    if site_id:
        qs = qs.filter(site_id=site_id)
    if from_ts:
        qs = qs.filter(submitted_at__gte=from_ts)
    if to_ts:
        qs = qs.filter(submitted_at__lte=to_ts)
    return qs


def get_record_scoped(*, user: User, record_id: uuid.UUID) -> DistributionRecord:
    record = (
        DistributionRecord.objects.select_related("site", "distributor_user").filter(id=record_id).first()
    )
    if record is None:
        raise NotFoundError("Delivery record not found.")
    if user.role != "ADMIN" and record.distributor_user_id != user.id:
        raise NotFoundError("Delivery record not found.")
    return record


def assignment_progress(*, assignment_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, Decimal]]:
    if not assignment_ids:
        return {}
    rows = (
        DistributionRecord.objects.filter(assignment_id__in=assignment_ids)
        .values("assignment_id", "status")
        .annotate(total=Sum("quantity_kg"))
    )
    result: dict[uuid.UUID, dict[str, Decimal]] = {}
    for row in rows:
        bucket = result.setdefault(
            row["assignment_id"],
            {"approved_kg": ZERO, "pending_kg": ZERO, "rejected_kg": ZERO},
        )
        if row["status"] == RecordStatus.APPROVED:
            bucket["approved_kg"] = Decimal(row["total"] or 0)
        elif row["status"] == RecordStatus.SUBMITTED:
            bucket["pending_kg"] = Decimal(row["total"] or 0)
        elif row["status"] == RecordStatus.REJECTED:
            bucket["rejected_kg"] = Decimal(row["total"] or 0)
    return result


def last_visit_at(*, site_id: uuid.UUID) -> datetime | None:
    return (
        DistributionRecord.objects.filter(site_id=site_id).order_by("-submitted_at").values_list(
            "submitted_at", flat=True
        ).first()
    )
