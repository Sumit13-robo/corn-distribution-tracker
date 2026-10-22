"""Evidence processing: upload intents, private ingestion, hashing, EXIF, flags.

Policy summary (docs/architecture/GEO_PHOTO_EVIDENCE.md):
- Intents are bound to the authenticated user, expire, and are consumed once.
- Uploads are validated by decoding the image server-side (never trusting the
  browser Content-Type), hashing content with SHA-256, and extracting EXIF when
  the browser preserved it.
- EXIF absence is informational (mobile browsers strip it); a mismatch with the
  browser GPS or capture-time drift is a flag for the reviewer, not an auto-reject.
- The content hash proves byte identity only - not when/where an image was captured.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from typing import Any

from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import GPSTAGS
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.core.security import digest_bytes_sha256_hex, opaque_object_key
from app.models import (
    CaptureSource,
    GeoFlag,
    IntentPurpose,
    PhotoEvidence,
    UploadIntent,
    User,
)
from app.services import settings_service
from app.services.audit_service import RequestContext, record_audit
from app.services.geo_service import geodesic_distance_m
from app.services.storage_service import StorageService, get_storage_service

MAGIC_SIGNATURES: dict[str, bytes] = {
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
    # RIFF....WEBP
    "image/webp": b"RIFF",
}


def sniff_content_type(data: bytes) -> str | None:
    for content_type, magic in MAGIC_SIGNATURES.items():
        if data[: len(magic)] == magic:
            if content_type == "image/webp" and data[8:12] != b"WEBP":
                continue
            return content_type
    return None


def create_upload_intent(
    db: Session, *, user: User, content_type: str, purpose: str, ctx: RequestContext
) -> tuple[UploadIntent, str | None]:
    settings = get_settings()
    if content_type not in settings.evidence_content_type_list:
        raise AppError(
            "Unsupported image type. Use JPEG, PNG or WebP.",
            details=[{"field": "content_type", "allowed": settings.evidence_content_type_list}],
        )
    intent = UploadIntent(
        user_id=user.id,
        purpose=IntentPurpose(purpose),
        content_type=content_type,
        max_bytes=settings.max_evidence_upload_bytes,
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )
    db.add(intent)
    db.flush()
    storage = get_storage_service()
    key = opaque_object_key("evidence")
    intent.storage_key = key
    db.flush()
    upload_url = storage.presigned_put(key, content_type, settings.max_evidence_upload_bytes)
    return intent, upload_url


def store_intent_upload(db: Session, *, intent: UploadIntent, data: bytes, content_type: str) -> None:
    """Local-mode upload path: the authenticated user PUTs bytes through the API."""
    if intent.consumed_at is not None:
        raise AppError("This upload was already completed.", code="DUPLICATE", status_code=409)
    if intent.expires_at < datetime.now(UTC):
        raise AppError(
            "This upload window has expired; start the submission again.",
            code="VALIDATION_ERROR",
            status_code=400,
        )
    if len(data) > intent.max_bytes:
        raise AppError("Image exceeds the maximum allowed size.", details=[{"field": "file"}])
    actual = sniff_content_type(data)
    if actual is None or actual != intent.content_type:
        raise AppError(
            "File content is not a supported image.", code="VALIDATION_ERROR", details=[{"field": "file"}]
        )
    storage = get_storage_service()
    assert intent.storage_key
    storage.put_object(intent.storage_key, data, actual)
    intent.received_bytes = len(data)
    intent.received_sha256_hex = digest_bytes_sha256_hex(data)
    db.flush()


def _exif_gps_dict(exif: Any) -> dict[str, Any]:
    gps_info = exif.get_ifd(0x8825) if hasattr(exif, "get_ifd") else {}
    result: dict[str, Any] = {}
    for key, value in (gps_info or {}).items():
        name = GPSTAGS.get(key, key)
        result[name] = value
    return result


def _dms_to_degrees(dms: Any, ref: Any) -> float | None:
    try:
        degrees, minutes, seconds = (float(c) for c in dms)
        value = degrees + minutes / 60 + seconds / 3600
        if ref in ("S", "W"):
            value = -value
        return value
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def extract_exif(data: bytes) -> dict[str, Any]:
    """Return {latitude, longitude, taken_at} when present; {} when absent."""
    try:
        image = Image.open(BytesIO(data))
        exif = image.getexif()  # public Pillow EXIF accessor (mirrors _getexif())
    except (UnidentifiedImageError, OSError, ValueError):
        return {}
    if not exif:
        return {}
    out: dict[str, Any] = {}
    gps = _exif_gps_dict(exif)
    lat = _dms_to_degrees(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef"))
    lng = _dms_to_degrees(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef"))
    if lat is not None and lng is not None:
        out["latitude"] = lat
        out["longitude"] = lng
    taken_raw = exif.get(36867) or exif.get(36868)  # DateTimeOriginal / DateTimeDigital
    if taken_raw:
        try:
            out["taken_at"] = datetime.strptime(str(taken_raw), "%Y:%m:%d %H:%M:%S").replace(tzinfo=UTC)
        except ValueError:
            pass
    return out


def attach_intents_to_record(
    db: Session,
    *,
    record,  # DistributionRecord
    user: User,
    site_latitude: Any,
    site_longitude: Any,
    specs: list[dict[str, Any]],
    ctx: RequestContext,
) -> list[PhotoEvidence]:
    """Validate + consume upload intents and create PhotoEvidence rows for a submission."""
    settings_row = settings_service.get_or_create_settings(db)
    storage: StorageService = get_storage_service()
    created: list[PhotoEvidence] = []
    for spec in specs:
        intent_id = spec.get("intent_id")
        capture_source = spec.get("capture_source")
        client_captured_at = spec.get("client_captured_at")
        if capture_source not in (
            CaptureSource.CAMERA.value,
            CaptureSource.FILE_PICKER.value,
            CaptureSource.OFFLINE_CAMERA.value,
        ):
            raise AppError("Unsupported capture source.", details=[{"field": "evidence.capture_source"}])
        intent = db.get(UploadIntent, intent_id)
        if intent is None or intent.user_id != user.id:
            raise NotFoundError("Upload intent not found.")
        if intent.consumed_at is not None:
            raise AppError("This upload was already used.", code="DUPLICATE", status_code=409)
        if intent.expires_at < datetime.now(UTC):
            raise AppError("This upload window has expired; recapture the photo.", code="VALIDATION_ERROR")
        if intent.storage_key is None or intent.received_sha256_hex is None:
            raise AppError("The photo has not finished uploading.", code="VALIDATION_ERROR")

        data = storage.get_object(intent.storage_key)
        actual_type = sniff_content_type(data)
        if actual_type is None:
            raise AppError(
                "File content is not a supported image.", code="VALIDATION_ERROR", details=[{"field": "file"}]
            )
        sha_hex = digest_bytes_sha256_hex(data)

        flags: list[str] = []
        metadata_check: dict[str, Any] = {"exif": "absent"}
        duplicate_of = None
        prior = db.scalar(
            select(PhotoEvidence)
            .where(PhotoEvidence.sha256_hex == sha_hex, PhotoEvidence.distribution_record_id.is_not(None))
            .limit(1)
        )
        if prior is not None:
            flags.append(GeoFlag.DUPLICATE_IMAGE_HASH.value)
            duplicate_of = prior.id

        exif = extract_exif(data)
        if exif:
            metadata_check["exif"] = "present"
            if exif.get("latitude") is not None and record.location_latitude is not None:
                distance = geodesic_distance_m(
                    Decimal(str(exif["latitude"])),
                    Decimal(str(exif["longitude"])),
                    record.location_latitude,
                    record.location_longitude,
                )
                metadata_check["exif_vs_reported_m"] = round(distance, 1)
                if distance > 1000:
                    flags.append(GeoFlag.EXIF_GPS_MISMATCH.value)
            if exif.get("taken_at") and record.submitted_at:
                drift = abs((exif["taken_at"] - record.submitted_at).total_seconds())
                metadata_check["capture_time_drift_s"] = drift
                if drift > settings_row.max_capture_time_drift_seconds:
                    flags.append(GeoFlag.CAPTURE_TIME_MISMATCH.value)

        if client_captured_at and record.submitted_at:
            drift = abs((client_captured_at - record.submitted_at.replace(tzinfo=UTC)).total_seconds())
            if drift > settings_row.max_capture_time_drift_seconds:
                if GeoFlag.CAPTURE_TIME_MISMATCH.value not in flags:
                    flags.append(GeoFlag.CAPTURE_TIME_MISMATCH.value)

        evidence = PhotoEvidence(
            distribution_record_id=record.id,
            uploader_user_id=user.id,
            storage_key=intent.storage_key,
            content_type=actual_type,
            size_bytes=len(data),
            sha256_hex=sha_hex,
            capture_source=CaptureSource(capture_source),
            client_captured_at=client_captured_at,
            server_received_at=datetime.now(UTC),
            exif_latitude=Decimal(str(exif["latitude"])) if exif.get("latitude") is not None else None,
            exif_longitude=Decimal(str(exif["longitude"])) if exif.get("longitude") is not None else None,
            exif_taken_at=exif.get("taken_at"),
            metadata_check_result=metadata_check,
            validation_flags=flags,
            duplicate_of_id=duplicate_of,
            lifecycle_status="ACTIVE",
        )
        db.add(evidence)
        intent.consumed_at = datetime.now(UTC)
        created.append(evidence)
    db.flush()
    return created


def issue_view_url(db: Session, *, user: User, evidence_id: uuid.UUID, ctx: RequestContext) -> dict[str, Any]:
    """Authorization-checked short-lived signed URL issuance for private evidence."""
    evidence = db.get(PhotoEvidence, evidence_id)
    if evidence is None:
        raise NotFoundError("Evidence not found.")
    if user.role != "ADMIN" and evidence.uploader_user_id != user.id:
        # 404 to avoid enumerating other users' evidence.
        raise NotFoundError("Evidence not found.")
    settings_row = settings_service.get_or_create_settings(db)
    storage = get_storage_service()
    url = storage.presigned_get(evidence.storage_key, str(evidence.id))
    record_audit(
        db,
        actor=user,
        action="evidence.signed_url_issued",
        target_type="photo_evidence",
        target_id=evidence.id,
        details={"ttl_seconds": settings_row and get_settings().storage_signed_url_ttl_seconds},
        ctx=ctx,
    )
    db.flush()
    return {
        "evidence_id": evidence.id,
        "url": url,
        "expires_in_seconds": get_settings().storage_signed_url_ttl_seconds,
    }


def load_evidence_bytes(db: Session, *, evidence_id: uuid.UUID) -> tuple[bytes, str]:
    """Used by the local-mode blob endpoint after signature verification."""
    evidence = db.get(PhotoEvidence, evidence_id)
    if evidence is None:
        raise NotFoundError("Evidence not found.")
    storage = get_storage_service()
    return storage.get_object(evidence.storage_key), evidence.content_type
