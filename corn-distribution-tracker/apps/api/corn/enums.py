"""Canonical enum values shared by models, services and presenters."""

from __future__ import annotations

from django.db import models


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Administrator"
    DISTRIBUTOR = "DISTRIBUTOR", "Distributor"


class CampaignStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    PAUSED = "PAUSED", "Paused"
    CLOSED = "CLOSED", "Closed"


class AccountType(models.TextChoices):
    CENTRAL = "CENTRAL", "Central"
    DISTRIBUTOR = "DISTRIBUTOR", "Distributor"
    SITE = "SITE", "Site"


class MovementType(models.TextChoices):
    RECEIPT = "RECEIPT", "Receipt"
    TRANSFER = "TRANSFER", "Transfer"
    DELIVERY = "DELIVERY", "Delivery"
    RETURN = "RETURN", "Return"
    LOSS = "LOSS", "Loss"
    ADJUSTMENT = "ADJUSTMENT", "Adjustment"
    REVERSAL = "REVERSAL", "Reversal"


class AssignmentStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    PAUSED = "PAUSED", "Paused"
    COMPLETE = "COMPLETE", "Complete"


class RecordStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"
    REVERSED = "REVERSED", "Reversed"


class GeoStatus(models.TextChoices):
    PASS = "PASS", "Pass"
    WARNING = "WARNING", "Warning"
    EXCEPTION = "EXCEPTION", "Exception"
    UNAVAILABLE = "UNAVAILABLE", "Unavailable"


class GeoFlag(models.TextChoices):
    GPS_MISSING = "GPS_MISSING", "GPS missing"
    GPS_STALE = "GPS_STALE", "GPS stale"
    GPS_LOW_ACCURACY = "GPS_LOW_ACCURACY", "GPS low accuracy"
    OUTSIDE_GEOFENCE = "OUTSIDE_GEOFENCE", "Outside geofence"
    EXIF_GPS_MISMATCH = "EXIF_GPS_MISMATCH", "EXIF GPS mismatch"
    CAPTURE_TIME_MISMATCH = "CAPTURE_TIME_MISMATCH", "Capture time mismatch"
    DUPLICATE_IMAGE_HASH = "DUPLICATE_IMAGE_HASH", "Duplicate image"
    UNEXPECTED_FILE_TYPE = "UNEXPECTED_FILE_TYPE", "Unexpected file type"
    LOCATION_EXCEPTION = "LOCATION_EXCEPTION", "Location exception"


class CaptureSource(models.TextChoices):
    CAMERA = "CAMERA", "Camera"
    FILE_PICKER = "FILE_PICKER", "File picker"
    OFFLINE_CAMERA = "OFFLINE_CAMERA", "Offline camera"


class EvidenceLifecycle(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACTIVE = "ACTIVE", "Active"
    SUPERSEDED = "SUPERSEDED", "Superseded"
    DELETED = "DELETED", "Deleted"


class DisplayUnit(models.TextChoices):
    KG = "KG", "Kilograms"
    QUINTAL = "QUINTAL", "Quintals"
    TONNE = "TONNE", "Tonnes"
    BAG = "BAG", "Bags"


class IntentPurpose(models.TextChoices):
    DISTRIBUTION_EVIDENCE = "DISTRIBUTION_EVIDENCE", "Distribution evidence"
