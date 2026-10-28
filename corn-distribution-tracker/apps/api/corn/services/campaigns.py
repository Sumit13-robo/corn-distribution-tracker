"""Campaign, site and assignment domain services."""

from __future__ import annotations

import uuid
import zoneinfo
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.db.models import Q
from django.utils.text import slugify

from ..enums import AssignmentStatus, CampaignStatus
from ..errors import AppError, ConflictError, NotFoundError
from ..geo import validate_coordinates
from ..models import Campaign, DistributionSite, DistributorAssignment, User
from ..units import convert_to_kg
from . import settings as settings_service_
from .audit import RequestContext, record_audit


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------
def _validate_window(starts_at: datetime | None, ends_at: datetime | None, timezone_name: str) -> None:
    if starts_at and ends_at and starts_at > ends_at:
        raise AppError("Campaign start must be before its end.", details=[{"field": "ends_at"}])
    try:
        zoneinfo.ZoneInfo(timezone_name)
    except Exception:
        raise AppError("Unknown timezone.", details=[{"field": "timezone"}]) from None


def create_campaign(*, admin: User, data: dict, ctx: RequestContext) -> Campaign:
    _validate_window(data.get("starts_at"), data.get("ends_at"), data.get("timezone") or "UTC")
    if Campaign.objects.filter(reference_code=data["reference_code"]).exists():
        raise AppError(
            "A campaign with this reference code already exists.",
            details=[{"field": "reference_code"}],
        )
    site_names = list(data.get("sites") or [])
    campaign = Campaign.objects.create(
        name=data["name"],
        reference_code=data["reference_code"],
        starts_at=data.get("starts_at"),
        ends_at=data.get("ends_at"),
        status=data.get("status", CampaignStatus.DRAFT),
        timezone=data.get("timezone") or "UTC",
        notes=data.get("notes"),
        created_by=admin,
    )
    # Site setup is part of campaign setup. The caller wraps this operation in
    # a transaction, so a bad site name does not leave a half-created campaign.
    for site_name in site_names:
        create_site(
            admin=admin,
            data={"name": site_name, "campaign_id": campaign.id},
            ctx=ctx,
        )
    record_audit(
        actor=admin,
        action="campaign.created",
        target_type="campaign",
        target_id=campaign.id,
        details={
            "reference_code": campaign.reference_code,
            "site_count": len(site_names),
        },
        ctx=ctx,
    )
    return campaign


def update_campaign(*, admin: User, campaign_id: uuid.UUID, data: dict, ctx: RequestContext) -> Campaign:
    campaign = Campaign.objects.filter(id=campaign_id).first()
    if campaign is None:
        raise NotFoundError("Campaign not found.")
    if (
        "status" in data
        and campaign.status == CampaignStatus.CLOSED
        and data["status"] != CampaignStatus.CLOSED
    ):
        raise AppError(
            "Closed campaigns cannot be reopened; create a new campaign.", code="ILLEGAL_STATE"
        )
    for key in ("name", "starts_at", "ends_at", "status", "timezone", "notes"):
        if key in data:
            setattr(campaign, key, data[key])
    _validate_window(campaign.starts_at, campaign.ends_at, campaign.timezone)
    campaign.save()
    record_audit(
        actor=admin,
        action="campaign.updated",
        target_type="campaign",
        target_id=campaign.id,
        details={"changed_fields": list(data.keys())},
        ctx=ctx,
    )
    return campaign


def list_campaigns(
    *, viewer: User, status: str | None, limit: int, offset: int
) -> tuple[list[Campaign], int]:
    qs = Campaign.objects.all()
    if viewer.role != "ADMIN":
        # Distributors can only discover campaigns they are assigned to. This
        # prevents draft campaign names/notes from leaking across the tenant.
        qs = qs.filter(assignments__distributor_user=viewer).distinct()
    if status:
        qs = qs.filter(status=status)
    total = qs.count()
    return list(qs.order_by("-created_at")[offset : offset + limit]), total


def get_campaign(*, viewer: User, campaign_id: uuid.UUID) -> Campaign:
    qs = Campaign.objects.all()
    if viewer.role != "ADMIN":
        qs = qs.filter(assignments__distributor_user=viewer).distinct()
    campaign = qs.filter(id=campaign_id).first()
    if campaign is None:
        raise NotFoundError("Campaign not found.")
    return campaign


# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------
def _generate_site_code(name: str) -> str:
    """Generate a human-readable unique code when the admin only enters a name."""
    base = slugify(name).upper()[:34] or f"SITE-{uuid.uuid4().hex[:6].upper()}"
    candidate = base
    suffix = 2
    while DistributionSite.objects.filter(site_code=candidate).exists():
        suffix_text = f"-{suffix}"
        candidate = f"{base[:40 - len(suffix_text)]}{suffix_text}"
        suffix += 1
    return candidate


def _site_location_values(site: DistributionSite) -> dict[str, str | None]:
    return {
        "latitude": str(site.latitude) if site.latitude is not None else None,
        "longitude": str(site.longitude) if site.longitude is not None else None,
    }


def create_site(*, admin: User, data: dict, ctx: RequestContext) -> DistributionSite:
    campaign = None
    if data.get("campaign_id"):
        campaign = Campaign.objects.filter(id=data["campaign_id"]).first()
        if campaign is None:
            raise NotFoundError("Campaign not found.")
    name = str(data["name"]).strip()
    if campaign is not None and DistributionSite.objects.filter(
        campaign=campaign, name__iexact=name
    ).exists():
        raise AppError(
            "A site with this name already exists in this campaign.",
            details=[{"field": "name"}],
        )

    raw_lat = data.get("latitude")
    raw_lng = data.get("longitude")
    lat = lng = None
    if raw_lat is not None and raw_lng is not None:
        lat, lng = validate_coordinates(Decimal(str(raw_lat)), Decimal(str(raw_lng)))
    elif raw_lat is not None or raw_lng is not None:
        raise AppError(
            "Site location requires both latitude and longitude (or neither).",
            details=[{"field": "latitude"}],
        )

    site_code = str(data.get("site_code") or "").strip() or _generate_site_code(name)
    if DistributionSite.objects.filter(site_code=site_code).exists():
        raise AppError("A site with this code already exists.", details=[{"field": "site_code"}])

    site = DistributionSite.objects.create(
        name=name,
        site_code=site_code,
        campaign=campaign,
        address_text=data.get("address_text"),
        region=data.get("region"),
        latitude=lat,
        longitude=lng,
        geofence_radius_m=data.get("geofence_radius_m") or 200,
        max_acceptable_accuracy_m=data.get("max_acceptable_accuracy_m"),
        is_active=True,
        notes=data.get("notes"),
        created_by=admin,
    )
    record_audit(
        actor=admin,
        action="site.created",
        target_type="site",
        target_id=site.id,
        details={
            "site_code": site.site_code,
            "campaign_id": str(campaign.id) if campaign else None,
            **_site_location_values(site),
        },
        ctx=ctx,
    )
    return site


def update_site(
    *, admin: User, site_id: uuid.UUID, data: dict, ctx: RequestContext
) -> DistributionSite:
    site = DistributionSite.objects.filter(id=site_id).first()
    if site is None:
        raise NotFoundError("Site not found.")
    if "name" in data and site.campaign_id is not None:
        new_name = str(data["name"]).strip()
        if DistributionSite.objects.filter(
            campaign_id=site.campaign_id, name__iexact=new_name
        ).exclude(id=site.id).exists():
            raise AppError(
                "A site with this name already exists in this campaign.",
                details=[{"field": "name"}],
            )
    location_changed = False
    before = _site_location_values(site)
    for key in (
        "name",
        "site_code",
        "address_text",
        "region",
        "notes",
        "geofence_radius_m",
        "max_acceptable_accuracy_m",
        "is_active",
    ):
        if key in data:
            if key == "site_code" and data[key] != site.site_code:
                if DistributionSite.objects.filter(site_code=data[key]).exclude(id=site.id).exists():
                    raise AppError(
                        "A site with this code already exists.", details=[{"field": "site_code"}]
                    )
            setattr(site, key, data[key])
    if "latitude" in data or "longitude" in data:
        raw_lat = data.get("latitude", site.latitude)
        raw_lng = data.get("longitude", site.longitude)
        if raw_lat is None and raw_lng is None:
            site.latitude = None
            site.longitude = None
        elif raw_lat is None or raw_lng is None:
            raise AppError(
                "Site location requires both latitude and longitude (or neither).",
                details=[{"field": "latitude"}],
            )
        else:
            site.latitude, site.longitude = validate_coordinates(
                Decimal(str(raw_lat)), Decimal(str(raw_lng))
            )
        location_changed = before != _site_location_values(site)
    site.save()
    if location_changed or "geofence_radius_m" in data:
        record_audit(
            actor=admin,
            action="site.location_changed",
            target_type="site",
            target_id=site.id,
            details={
                "before": before,
                "after": _site_location_values(site),
                "geofence_radius_m": site.geofence_radius_m,
            },
            ctx=ctx,
        )
    record_audit(
        actor=admin,
        action="site.updated",
        target_type="site",
        target_id=site.id,
        details={"changed_fields": list(data.keys())},
        ctx=ctx,
    )
    return site


def deactivate_site(*, admin: User, site_id: uuid.UUID, ctx: RequestContext) -> DistributionSite:
    site = DistributionSite.objects.filter(id=site_id).first()
    if site is None:
        raise NotFoundError("Site not found.")
    site.is_active = False
    site.save(update_fields=["is_active", "updated_at"])
    record_audit(
        actor=admin, action="site.deactivated", target_type="site", target_id=site.id, ctx=ctx
    )
    return site


def list_sites(
    *,
    active_only: bool,
    search: str | None,
    campaign_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[DistributionSite], int]:
    qs = DistributionSite.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(site_code__icontains=search))
    if campaign_id:
        # Direct campaign ownership is authoritative. The assignment fallback
        # keeps legacy sites visible until the data migration/backfill runs.
        qs = qs.filter(
            Q(campaign_id=campaign_id) | Q(assignments__campaign_id=campaign_id)
        ).distinct()
    total = qs.count()
    return list(qs.order_by("name")[offset : offset + limit]), total


def get_site(site_id: uuid.UUID) -> DistributionSite:
    site = DistributionSite.objects.filter(id=site_id).first()
    if site is None:
        raise NotFoundError("Site not found.")
    return site


def assigned_sites(*, user: User, search: str | None, limit: int, offset: int):
    qs = DistributionSite.objects.filter(assignments__distributor_user_id=user.id).distinct()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(site_code__icontains=search))
    total = qs.count()
    return list(qs.order_by("site_code")[offset : offset + limit]), total


# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------
def create_assignment(*, admin: User, data: dict, ctx: RequestContext) -> DistributorAssignment:
    site = DistributionSite.objects.filter(id=data["site_id"]).first()
    if site is None or not site.is_active:
        raise NotFoundError("Site not found or inactive.")
    distributor = User.objects.filter(id=data["distributor_user_id"]).first()
    if distributor is None or distributor.role != "DISTRIBUTOR" or not distributor.is_active:
        raise NotFoundError("Distributor not found.")
    campaign = None
    if data.get("campaign_id"):
        campaign = Campaign.objects.filter(id=data["campaign_id"]).first()
        if campaign is None:
            raise NotFoundError("Campaign not found.")
    if campaign is not None and site.campaign_id not in (None, campaign.id):
        raise AppError(
            "This site belongs to another campaign. Add a site inside this campaign instead.",
            details=[{"field": "site_id"}],
        )
    if campaign is not None and site.campaign_id is None:
        # Legacy/global sites become campaign-scoped when first assigned.
        site.campaign = campaign
        site.save(update_fields=["campaign", "updated_at"])
    if campaign is None and site.campaign_id is not None:
        campaign = site.campaign
    settings_row = settings_service_.get_or_create_settings()
    kg = convert_to_kg(
        Decimal(str(data["target_quantity"])), data.get("unit", "KG"), settings_row.kg_per_bag
    )
    open_conflict = DistributorAssignment.objects.filter(
        campaign=campaign,
        site=site,
        distributor_user=distributor,
        status__in=[AssignmentStatus.ACTIVE, AssignmentStatus.PAUSED],
    ).exists()
    if open_conflict:
        raise ConflictError(
            "An open assignment already exists for this distributor, campaign and site.",
            code="DUPLICATE",
        )
    assignment = DistributorAssignment.objects.create(
        campaign=campaign,
        site=site,
        distributor_user=distributor,
        target_quantity_kg=kg,
        due_at=data.get("due_at"),
        status=AssignmentStatus.ACTIVE,
        notes=data.get("notes"),
        created_by=admin,
    )
    record_audit(
        actor=admin,
        action="assignment.created",
        target_type="assignment",
        target_id=assignment.id,
        details={
            "target_kg": str(kg),
            "site_id": str(site.id),
            "distributor_user_id": str(distributor.id),
        },
        ctx=ctx,
    )
    return assignment


def update_assignment(
    *, admin: User, assignment_id: uuid.UUID, data: dict, ctx: RequestContext
) -> DistributorAssignment:
    assignment = (
        DistributorAssignment.objects.select_for_update().filter(id=assignment_id).first()
    )
    if assignment is None:
        raise NotFoundError("Assignment not found.")
    new_status = data.get("status", assignment.status)
    if new_status in (AssignmentStatus.ACTIVE, AssignmentStatus.PAUSED):
        duplicate_qs = DistributorAssignment.objects.filter(
            site_id=assignment.site_id,
            distributor_user_id=assignment.distributor_user_id,
            status__in=[AssignmentStatus.ACTIVE, AssignmentStatus.PAUSED],
        ).exclude(id=assignment.id)
        if assignment.campaign_id is None:
            duplicate_qs = duplicate_qs.filter(campaign__isnull=True)
        else:
            duplicate_qs = duplicate_qs.filter(campaign_id=assignment.campaign_id)
        duplicate = duplicate_qs.exists()
        if duplicate:
            raise ConflictError(
                "Another open assignment already exists for this distributor, campaign and site.",
                code="DUPLICATE",
            )
    for key in ("due_at", "status", "notes"):
        if key in data:
            setattr(assignment, key, data[key])
    if "target_quantity" in data:
        settings_row = settings_service_.get_or_create_settings()
        assignment.target_quantity_kg = convert_to_kg(
            Decimal(str(data["target_quantity"])),
            data.get("unit", "KG"),
            settings_row.kg_per_bag,
        )
    assignment.save()
    record_audit(
        actor=admin,
        action="assignment.updated",
        target_type="assignment",
        target_id=assignment.id,
        details={"changed_fields": list(data.keys())},
        ctx=ctx,
    )
    return assignment


def get_assignment_scoped(*, user: User, assignment_id: uuid.UUID) -> DistributorAssignment:
    assignment = DistributorAssignment.objects.filter(id=assignment_id).first()
    if assignment is None:
        raise NotFoundError("Assignment not found.")
    if user.role != "ADMIN" and assignment.distributor_user_id != user.id:
        raise NotFoundError("Assignment not found.")
    return assignment


def list_assignments(
    *, user: User, campaign_id: uuid.UUID | None, limit: int, offset: int
) -> tuple[list[DistributorAssignment], int]:
    qs = DistributorAssignment.objects.all()
    if user.role != "ADMIN":
        qs = qs.filter(distributor_user_id=user.id)
    if campaign_id:
        qs = qs.filter(campaign_id=campaign_id)
    total = qs.count()
    return list(qs.order_by("-created_at")[offset : offset + limit]), total


def distributor_me_assignments(*, user: User) -> list[dict[str, Any]]:
    if user.role == "ADMIN":
        raise AppError("This endpoint is for distributors.", status_code=403)
    from .distribution import assignment_progress

    rows = list(
        DistributorAssignment.objects.filter(distributor_user_id=user.id).order_by("-created_at")
    )
    progress = assignment_progress(assignment_ids=[row.id for row in rows])
    sites = {site.id: site for site in DistributionSite.objects.filter(id__in={a.site_id for a in rows})}
    result = []
    zero = Decimal(0)
    for assignment in rows:
        site = sites.get(assignment.site_id)
        agg = progress.get(
            assignment.id, {"approved_kg": zero, "pending_kg": zero, "rejected_kg": zero}
        )
        target = Decimal(assignment.target_quantity_kg)
        approved = Decimal(agg["approved_kg"])
        from ..presenters import site_out

        result.append(
            {
                "assignment_id": assignment.id,
                "campaign_id": assignment.campaign_id,
                "due_at": assignment.due_at,
                "status": assignment.status,
                "target_kg": target,
                "approved_kg": approved,
                "pending_kg": Decimal(agg["pending_kg"]),
                "remaining_target_kg": max(target - approved, zero),
                "over_target_kg": max(approved - target, zero),
                "site": site_out(site, include_notes=False) if site else None,
            }
        )
    return result
