"""Response presenters. Quantities always leave the API as decimal strings."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from .models import (
    AuditEvent,
    Campaign,
    DistributionRecord,
    DistributionSite,
    DistributorAssignment,
    OrganizationSettings,
    PhotoEvidence,
    StockMovement,
    User,
)


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def dec(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


KG_QUANTUM = Decimal("0.001")


def jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return iso(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {
            key: (
                str(item.quantize(KG_QUANTUM))
                if key.endswith("_kg") and isinstance(item, Decimal)
                else jsonable(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [jsonable(item) for item in value]
    return value


def page(items: list[Any], total: int, limit: int, offset: int) -> dict[str, Any]:
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def user_out(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "is_active": user.is_active,
        "must_reset_password": user.must_reset_password,
        "last_login_at": iso(user.last_login),
    }


def distributor_out(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "is_active": user.is_active,
        "must_reset_password": user.must_reset_password,
        "last_login_at": iso(user.last_login),
        "created_at": iso(user.created_at),
    }


def campaign_out(campaign: Campaign, *, include_notes: bool = True) -> dict[str, Any]:
    return {
        "id": str(campaign.id),
        "name": campaign.name,
        "reference_code": campaign.reference_code,
        "starts_at": iso(campaign.starts_at),
        "ends_at": iso(campaign.ends_at),
        "status": campaign.status,
        "timezone": campaign.timezone,
        "notes": campaign.notes if include_notes else None,
        "created_at": iso(campaign.created_at),
    }


def site_out(site: DistributionSite, *, include_notes: bool = True) -> dict[str, Any]:
    return {
        "id": str(site.id),
        "name": site.name,
        "site_code": site.site_code,
        "campaign_id": str(site.campaign_id) if site.campaign_id else None,
        "address_text": site.address_text,
        "region": site.region,
        "latitude": dec(site.latitude),
        "longitude": dec(site.longitude),
        "geofence_radius_m": site.geofence_radius_m,
        "max_acceptable_accuracy_m": site.max_acceptable_accuracy_m,
        "is_active": site.is_active,
        "notes": site.notes if include_notes else None,
        "created_at": iso(site.created_at),
        "updated_at": iso(site.updated_at),
    }


def assignment_out(assignment: DistributorAssignment, *, include_notes: bool = True) -> dict[str, Any]:
    return {
        "id": str(assignment.id),
        "campaign_id": str(assignment.campaign_id) if assignment.campaign_id else None,
        "site_id": str(assignment.site_id),
        "distributor_user_id": str(assignment.distributor_user_id),
        "target_quantity_kg": dec(assignment.target_quantity_kg),
        "due_at": iso(assignment.due_at),
        "status": assignment.status,
        "notes": assignment.notes if include_notes else None,
        "created_at": iso(assignment.created_at),
    }


def movement_out(movement: StockMovement) -> dict[str, Any]:
    reversal = getattr(movement, "reversal", None)
    return {
        "id": str(movement.id),
        "movement_type": movement.movement_type,
        "source_account_id": str(movement.source_account_id) if movement.source_account_id else None,
        "destination_account_id": (
            str(movement.destination_account_id) if movement.destination_account_id else None
        ),
        "quantity_kg": dec(movement.quantity_kg),
        "reference_type": movement.reference_type,
        "reference_id": str(movement.reference_id) if movement.reference_id else None,
        "idempotency_scope": movement.idempotency_scope or None,
        "idempotency_key": movement.idempotency_key,
        "occurred_at": iso(movement.occurred_at),
        "posted_at": iso(movement.posted_at),
        "created_by": str(movement.created_by_id) if movement.created_by_id else None,
        "reason": movement.reason,
        "reversal_of_id": str(movement.reversal_of_id) if movement.reversal_of_id else None,
        "reversed_by_id": str(reversal.id) if reversal is not None else None,
        "movement_metadata": movement.movement_metadata or {},
    }


def evidence_out(evidence: PhotoEvidence) -> dict[str, Any]:
    return {
        "id": str(evidence.id),
        "content_type": evidence.content_type,
        "size_bytes": evidence.size_bytes,
        "sha256_hex": evidence.sha256_hex,
        "capture_source": evidence.capture_source,
        "client_captured_at": iso(evidence.client_captured_at),
        "server_received_at": iso(evidence.server_received_at),
        "exif_latitude": dec(evidence.exif_latitude),
        "exif_longitude": dec(evidence.exif_longitude),
        "exif_taken_at": iso(evidence.exif_taken_at),
        "metadata_check_result": evidence.metadata_check_result or {},
        "validation_flags": evidence.validation_flags or [],
        "lifecycle_status": evidence.lifecycle_status,
    }


def distribution_out(
    record: DistributionRecord, evidence: list[PhotoEvidence] | None = None
) -> dict[str, Any]:
    return {
        "id": str(record.id),
        "campaign_id": str(record.campaign_id) if record.campaign_id else None,
        "assignment_id": str(record.assignment_id),
        "site_id": str(record.site_id),
        "site_code": record.site.site_code,
        "site_name": record.site.name,
        "distributor_user_id": str(record.distributor_user_id),
        "distributor_name": record.distributor_user.display_name,
        "quantity_kg": dec(record.quantity_kg),
        "status": record.status,
        "client_created_at": iso(record.client_created_at),
        "submitted_at": iso(record.submitted_at),
        "reviewed_at": iso(record.reviewed_at),
        "reviewed_by": str(record.reviewed_by_id) if record.reviewed_by_id else None,
        "review_reason": record.review_reason,
        "review_exception_reason": record.review_exception_reason,
        "reversed_at": iso(record.reversed_at),
        "reversed_by": str(record.reversed_by_id) if record.reversed_by_id else None,
        "reversal_reason": record.reversal_reason,
        "stock_movement_id": str(record.stock_movement_id) if record.stock_movement_id else None,
        "notes": record.notes,
        "location_latitude": dec(record.location_latitude),
        "location_longitude": dec(record.location_longitude),
        "location_accuracy_m": dec(record.location_accuracy_m),
        "location_timestamp": iso(record.location_timestamp),
        "device_reported_location_time": iso(record.device_reported_location_time),
        "distance_to_site_m": dec(record.distance_to_site_m),
        "geo_status": record.geo_status,
        "geo_flags": list(record.geo_flags or []),
        "evidence": [evidence_out(item) for item in (evidence or [])],
        "created_at": iso(record.created_at),
        "updated_at": iso(record.updated_at),
    }


def settings_out(settings: OrganizationSettings) -> dict[str, Any]:
    return {
        "timezone": settings.timezone,
        "default_display_unit": settings.default_display_unit,
        "kg_per_bag": dec(settings.kg_per_bag),
        "default_geofence_radius_m": settings.default_geofence_radius_m,
        "max_acceptable_gps_accuracy_m": settings.max_acceptable_gps_accuracy_m,
        "max_location_age_seconds": settings.max_location_age_seconds,
        "max_capture_time_drift_seconds": settings.max_capture_time_drift_seconds,
        "updated_at": iso(settings.updated_at),
    }


def audit_event_out(event: AuditEvent) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
        "action": event.action,
        "target_type": event.target_type,
        "target_id": str(event.target_id) if event.target_id else None,
        "occurred_at": iso(event.occurred_at),
        "request_id": event.request_id,
        "reason": event.reason,
        "details": event.details or {},
        "ip_address": event.ip_address,
        "user_agent_abridged": event.user_agent_abridged,
    }
