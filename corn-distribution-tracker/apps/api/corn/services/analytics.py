"""Analytics and reporting formulas (canonical per the domain docs)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.db.models import Sum

from ..enums import AccountType, RecordStatus
from ..models import (
    DistributionRecord,
    DistributionSite,
    DistributorAssignment,
    PhotoEvidence,
    StockAccount,
    User,
)
from .inventory import posted_balance_kg, reserved_kg

# Location metadata is informational; only non-location evidence integrity
# checks count as flagged.
_CRITICAL_EVIDENCE_FLAGS = {
    "UNEXPECTED_FILE_TYPE",
    "CAPTURE_TIME_MISMATCH",
    "DUPLICATE_IMAGE_HASH",
}
ZERO = Decimal("0")


def _records_query(
    *,
    scope_user: User | None,
    campaign_id: uuid.UUID | None,
    from_ts: datetime | None,
    to_ts: datetime | None,
):
    qs = DistributionRecord.objects.all()
    if scope_user is not None:
        qs = qs.filter(distributor_user_id=scope_user.id)
    if campaign_id:
        qs = qs.filter(campaign_id=campaign_id)
    if from_ts:
        qs = qs.filter(submitted_at__gte=from_ts)
    if to_ts:
        qs = qs.filter(submitted_at__lte=to_ts)
    return qs


def overview(
    *,
    scope_user: User | None,
    campaign_id: uuid.UUID | None,
    from_ts: datetime | None,
    to_ts: datetime | None,
) -> dict[str, Any]:
    records = list(
        _records_query(scope_user=scope_user, campaign_id=campaign_id, from_ts=from_ts, to_ts=to_ts)
    )
    submitted_pending = sum(
        (Decimal(record.quantity_kg) for record in records if record.status == RecordStatus.SUBMITTED),
        ZERO,
    )
    approved_delivered = sum(
        (Decimal(record.quantity_kg) for record in records if record.status == RecordStatus.APPROVED),
        ZERO,
    )
    rejected = sum(
        (Decimal(record.quantity_kg) for record in records if record.status == RecordStatus.REJECTED),
        ZERO,
    )
    open_review = sum(1 for record in records if record.status == RecordStatus.SUBMITTED)

    # Targets are defined by assignments, not by the subset that happens to
    # have submissions in the selected date window. Completed and unvisited
    # assignments still contribute to the all-time target, and approved totals
    # used for target math are intentionally not date-filtered.
    assignments_qs = DistributorAssignment.objects.all()
    if scope_user is not None:
        assignments_qs = assignments_qs.filter(distributor_user_id=scope_user.id)
    if campaign_id is not None:
        assignments_qs = assignments_qs.filter(campaign_id=campaign_id)
    assignments = list(assignments_qs)
    approved_qs = DistributionRecord.objects.filter(status=RecordStatus.APPROVED)
    if scope_user is not None:
        approved_qs = approved_qs.filter(distributor_user_id=scope_user.id)
    if campaign_id is not None:
        approved_qs = approved_qs.filter(campaign_id=campaign_id)
    approved_by_assignment: dict[uuid.UUID, Decimal] = {
        row["assignment_id"]: Decimal(row["total"] or 0)
        for row in approved_qs.values("assignment_id").annotate(total=Sum("quantity_kg"))
    }
    targets = ZERO
    remaining = ZERO
    overage = ZERO
    for assignment in assignments:
        targets += Decimal(assignment.target_quantity_kg)
        approved_for = approved_by_assignment.get(assignment.id, ZERO)
        remaining += max(Decimal(assignment.target_quantity_kg) - approved_for, ZERO)
        overage += max(approved_for - Decimal(assignment.target_quantity_kg), ZERO)

    approved_records = [record for record in records if record.status == RecordStatus.APPROVED]
    approved_ids = [record.id for record in approved_records]
    evidence_counts: dict[uuid.UUID, int] = {}
    flagged_record_ids: set[uuid.UUID] = {
        record.id
        for record in records
        if set(record.geo_flags or []) & _CRITICAL_EVIDENCE_FLAGS
    }
    if approved_ids:
        for evidence in PhotoEvidence.objects.filter(distribution_record_id__in=approved_ids):
            owner_id = evidence.distribution_record_id
            if owner_id is None:
                continue
            evidence_counts[owner_id] = evidence_counts.get(owner_id, 0) + 1
    with_evidence = sum(1 for record in approved_records if evidence_counts.get(record.id, 0) > 0)

    return {
        "filters": {"campaign_id": campaign_id, "from": from_ts, "to": to_ts},
        "stock": account_stock(scope_user=scope_user),
        "submitted_pending_kg": submitted_pending,
        "approved_delivered_kg": approved_delivered,
        "rejected_kg": rejected,
        "open_review_count": open_review,
        "target_kg": targets,
        "remaining_target_kg": remaining,
        "over_target_kg": overage,
        "evidence_completeness": {
            "approved_with_evidence": with_evidence,
            "approved_total": len(approved_records),
            "ratio": (with_evidence / len(approved_records)) if approved_records else None,
        },
        "flagged_record_count": len(flagged_record_ids),
        "unit": "kg",
    }


def account_stock(*, scope_user: User | None) -> dict[str, Any]:
    result = {
        "central_on_hand_kg": ZERO,
        "distributor_held_kg": ZERO,
        "site_stock_kg": ZERO,
    }
    scoped_site_ids: set[uuid.UUID] | None = None
    if scope_user is not None:
        scoped_site_ids = set(
            DistributorAssignment.objects.filter(distributor_user_id=scope_user.id)
            .values_list("site_id", flat=True)
            .distinct()
        )
    reserved_total = ZERO
    for account in StockAccount.objects.all():
        balance = posted_balance_kg(account.id)
        if account.account_type == AccountType.CENTRAL:
            if scope_user is None:
                result["central_on_hand_kg"] += balance
        elif account.account_type == AccountType.DISTRIBUTOR:
            if scope_user is None or account.owner_user_id == scope_user.id:
                result["distributor_held_kg"] += balance
                if account.owner_user_id:
                    reserved_total += reserved_kg(account.owner_user_id)
        elif account.account_type == AccountType.SITE:
            if scope_user is None or (
                scoped_site_ids is not None
                and account.site_id is not None
                and account.site_id in scoped_site_ids
            ):
                result["site_stock_kg"] += balance
    result["reserved_pending_kg"] = reserved_total
    return result


def distributor_performance(
    *, campaign_id: uuid.UUID | None, from_ts: datetime | None, to_ts: datetime | None
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for distributor in User.objects.filter(role="DISTRIBUTOR").order_by("display_name"):
        records = list(
            _records_query(
                scope_user=distributor,
                campaign_id=campaign_id,
                from_ts=from_ts,
                to_ts=to_ts,
            )
        )
        assignments = DistributorAssignment.objects.filter(
            distributor_user_id=distributor.id,
            status__in=["ACTIVE", "PAUSED"],
        )
        if campaign_id:
            assignments = assignments.filter(campaign_id=campaign_id)
        target = assignments.aggregate(total=Sum("target_quantity_kg"))["total"] or ZERO
        approved = sum(
            (Decimal(record.quantity_kg) for record in records if record.status == RecordStatus.APPROVED),
            ZERO,
        )
        pending = sum(
            (Decimal(record.quantity_kg) for record in records if record.status == RecordStatus.SUBMITTED),
            ZERO,
        )
        rejected = sum(
            (Decimal(record.quantity_kg) for record in records if record.status == RecordStatus.REJECTED),
            ZERO,
        )
        flagged = sum(
            1 for record in records if set(record.geo_flags or []) & _CRITICAL_EVIDENCE_FLAGS
        )
        exceptions = sum(
            1
            for record in records
            if record.status == RecordStatus.APPROVED and record.review_exception_reason
        )
        account = StockAccount.objects.filter(owner_user_id=distributor.id).first()
        balance = posted_balance_kg(account.id) if account else ZERO
        out.append(
            {
                "distributor_user_id": distributor.id,
                "display_name": distributor.display_name,
                "email": distributor.email,
                "is_active": distributor.is_active,
                "target_kg": Decimal(target),
                "submitted_kg": approved + pending + rejected,
                "approved_kg": approved,
                "pending_kg": pending,
                "rejected_kg": rejected,
                "remaining_target_kg": max(Decimal(target) - approved, ZERO),
                "over_target_kg": max(approved - Decimal(target), ZERO),
                "stock_balance_kg": balance,
                "flagged_submissions": flagged,
                "approved_with_exception": exceptions,
                "denominator_note": (
                    "Submitted totals are approved + pending + rejected within the selected window."
                ),
            }
        )
    return out


def site_performance(
    *, campaign_id: uuid.UUID | None, from_ts: datetime | None, to_ts: datetime | None
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    sites = DistributionSite.objects.order_by("site_code")
    if campaign_id:
        sites = sites.filter(campaign_id=campaign_id)
    for site in sites:
        records = list(
            _records_query(scope_user=None, campaign_id=campaign_id, from_ts=from_ts, to_ts=to_ts).filter(
                site=site
            )
        )
        assignments = DistributorAssignment.objects.filter(
            site=site, status__in=["ACTIVE", "PAUSED"]
        )
        if campaign_id:
            assignments = assignments.filter(campaign_id=campaign_id)
        target = assignments.aggregate(total=Sum("target_quantity_kg"))["total"] or ZERO
        approved = sum(
            (Decimal(record.quantity_kg) for record in records if record.status == RecordStatus.APPROVED),
            ZERO,
        )
        pending = sum(
            (Decimal(record.quantity_kg) for record in records if record.status == RecordStatus.SUBMITTED),
            ZERO,
        )
        rejected = sum(
            (Decimal(record.quantity_kg) for record in records if record.status == RecordStatus.REJECTED),
            ZERO,
        )
        record_ids = [record.id for record in records]
        evidence_status = "NONE"
        if record_ids:
            count = PhotoEvidence.objects.filter(distribution_record_id__in=record_ids).count()
            evidence_status = "EVIDENCE_PRESENT" if count > 0 else "EVIDENCE_MISSING"
        last_visit = (
            DistributionRecord.objects.filter(site=site)
            .order_by("-submitted_at")
            .values_list("submitted_at", flat=True)
            .first()
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
                "remaining_target_kg": max(Decimal(target) - approved, ZERO),
                "last_visit_at": last_visit,
                "evidence_status": evidence_status,
                "denominator_note": (
                    "Target basis: open assignment targets for this site in the selected campaign."
                ),
            }
        )
    return out


def map_deliveries(
    *,
    bbox: tuple[float, float, float, float] | None,
    campaign_id: uuid.UUID | None,
    distributor_user_id: uuid.UUID | None,
) -> list[dict[str, Any]]:
    """Delivery points with a captured distributor location.

    The admin map intentionally plots where a distributor recorded a delivery,
    not the site's reference coordinates and not sites that have no delivery.
    A submitted record is a delivery claim awaiting review; an approved record
    is verified delivery history. Rejected/cancelled claims are excluded.
    """
    records = (
        DistributionRecord.objects.filter(
            status__in=[RecordStatus.SUBMITTED, RecordStatus.APPROVED],
            location_latitude__isnull=False,
            location_longitude__isnull=False,
        )
        .select_related("site", "distributor_user")
        .order_by("-submitted_at")
    )
    if campaign_id:
        records = records.filter(campaign_id=campaign_id)
    if distributor_user_id:
        records = records.filter(distributor_user_id=distributor_user_id)
    if bbox is not None:
        min_lng, min_lat, max_lng, max_lat = bbox
        records = records.filter(
            location_latitude__gte=Decimal(str(min_lat)),
            location_latitude__lte=Decimal(str(max_lat)),
            location_longitude__gte=Decimal(str(min_lng)),
            location_longitude__lte=Decimal(str(max_lng)),
        )
    return [
        {
            "id": record.id,
            "site_id": record.site_id,
            "site_code": record.site.site_code,
            "site_name": record.site.name,
            "campaign_id": record.campaign_id,
            "distributor_user_id": record.distributor_user_id,
            "distributor_name": record.distributor_user.display_name,
            "quantity_kg": record.quantity_kg,
            "status": record.status,
            "submitted_at": record.submitted_at,
            "location_latitude": record.location_latitude,
            "location_longitude": record.location_longitude,
            "location_accuracy_m": record.location_accuracy_m,
            "location_timestamp": record.location_timestamp,
        }
        for record in records
    ]


def map_sites(
    *,
    bbox: tuple[float, float, float, float] | None,
    campaign_id: uuid.UUID | None,
    distributor_user_id: uuid.UUID | None,
) -> list[dict[str, Any]]:
    sites = DistributionSite.objects.filter(
        latitude__isnull=False, longitude__isnull=False
    ).order_by("site_code")
    if campaign_id:
        sites = sites.filter(campaign_id=campaign_id)
    if bbox is not None:
        min_lng, min_lat, max_lng, max_lat = bbox
        sites = sites.filter(
            latitude__gte=Decimal(str(min_lat)),
            latitude__lte=Decimal(str(max_lat)),
            longitude__gte=Decimal(str(min_lng)),
            longitude__lte=Decimal(str(max_lng)),
        )
    out = []
    for site in sites:
        records = DistributionRecord.objects.filter(site=site)
        if campaign_id:
            records = records.filter(campaign_id=campaign_id)
        if distributor_user_id:
            records = records.filter(distributor_user_id=distributor_user_id)
        record_list = list(records)
        assignments = DistributorAssignment.objects.filter(site=site, status__in=["ACTIVE", "PAUSED"])
        if campaign_id:
            assignments = assignments.filter(campaign_id=campaign_id)
        target = assignments.aggregate(total=Sum("target_quantity_kg"))["total"] or ZERO
        approved = sum(
            (Decimal(record.quantity_kg) for record in record_list if record.status == RecordStatus.APPROVED),
            ZERO,
        )
        pending = sum(
            (
                Decimal(record.quantity_kg)
                for record in record_list
                if record.status == RecordStatus.SUBMITTED
            ),
            ZERO,
        )
        remaining = max(Decimal(target) - approved, ZERO)
        if approved > 0 and pending == 0 and remaining == 0:
            status = "COMPLETE"
        elif pending > 0:
            status = "PENDING"
        elif approved > 0:
            status = "IN_PROGRESS"
        else:
            status = "NO_ACTIVITY"
        last_visit = max((record.submitted_at for record in record_list), default=None)
        flagged = any(
            set(record.geo_flags or []) & _CRITICAL_EVIDENCE_FLAGS for record in record_list
        )
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
                "submission_count": len(record_list),
                "status": status,
                "last_visit_at": last_visit,
                "has_flagged_evidence": flagged,
            }
        )
    return out
