"""Shared enum values. These literals are canonical per docs/architecture/API_CONTRACT.md
and docs/architecture/DOMAIN_MODEL.md; frontend types must mirror them."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "ADMIN"
    DISTRIBUTOR = "DISTRIBUTOR"


class CampaignStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"


class AccountType(StrEnum):
    CENTRAL = "CENTRAL"
    DISTRIBUTOR = "DISTRIBUTOR"
    SITE = "SITE"


class MovementType(StrEnum):
    RECEIPT = "RECEIPT"
    TRANSFER = "TRANSFER"
    DELIVERY = "DELIVERY"
    RETURN = "RETURN"
    LOSS = "LOSS"
    ADJUSTMENT = "ADJUSTMENT"
    REVERSAL = "REVERSAL"


class AssignmentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETE = "COMPLETE"


class RecordStatus(StrEnum):
    DRAFT = "DRAFT"  # kept for future server-draft support; field drafts live on the client
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class GeoStatus(StrEnum):
    PASS = "PASS"  # noqa: S105 - review verdict literal, not a credential
    WARNING = "WARNING"
    EXCEPTION = "EXCEPTION"
    UNAVAILABLE = "UNAVAILABLE"


class GeoFlag(StrEnum):
    GPS_MISSING = "GPS_MISSING"
    GPS_STALE = "GPS_STALE"
    GPS_LOW_ACCURACY = "GPS_LOW_ACCURACY"
    OUTSIDE_GEOFENCE = "OUTSIDE_GEOFENCE"
    EXIF_GPS_MISMATCH = "EXIF_GPS_MISMATCH"
    CAPTURE_TIME_MISMATCH = "CAPTURE_TIME_MISMATCH"
    DUPLICATE_IMAGE_HASH = "DUPLICATE_IMAGE_HASH"
    UNEXPECTED_FILE_TYPE = "UNEXPECTED_FILE_TYPE"
    LOCATION_EXCEPTION = "LOCATION_EXCEPTION"


class CaptureSource(StrEnum):
    CAMERA = "CAMERA"
    FILE_PICKER = "FILE_PICKER"
    OFFLINE_CAMERA = "OFFLINE_CAMERA"


class EvidenceLifecycle(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    DELETED = "DELETED"


class DisplayUnit(StrEnum):
    KG = "KG"
    QUINTAL = "QUINTAL"
    TONNE = "TONNE"
    BAG = "BAG"


class IntentPurpose(StrEnum):
    DISTRIBUTION_EVIDENCE = "DISTRIBUTION_EVIDENCE"
