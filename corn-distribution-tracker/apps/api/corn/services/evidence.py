"""Evidence upload intents, private ingestion, hashing and EXIF flags."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from typing import Any

from django.conf import settings
from django.utils import timezone
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import GPSTAGS

from ..enums import CaptureSource, EvidenceLifecycle, GeoFlag, IntentPurpose
from ..errors import AppError, ConflictError, NotFoundError
from ..geo import geodesic_distance_m
from ..models import DistributionRecord, PhotoEvidence, UploadIntent, User
from ..security import digest_bytes_sha256_hex, opaque_object_key
from ..storage import StorageService, get_storage_service
from . import settings as settings_service_
from .audit import RequestContext, record_audit

MAGIC_SIGNATURES: dict[str, bytes] = {
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/webp": b"RIFF",
}


def sniff_content_type(data: bytes) -> str | None:
    for content_type, magic in MAGIC_SIGNATURES.items():
        if data[: len(magic)] == magic:
            if content_type == "image/webp" and data[8:12] != b"WEBP":
                continue
            return content_type
    return None


def validate_image_bytes(data: bytes) -> tuple[str, int, int]:
    """Decode the image, enforce the pixel cap and return its real type/size.

    Magic-byte checks alone accept truncated or deliberately malformed files.
    Pillow verifies the container and fully decodes the image before any bytes
    are persisted or attached to a delivery.
    """
    actual = sniff_content_type(data)
    if actual is None:
        raise AppError(
            "File content is not a supported image.",
            code="VALIDATION_ERROR",
            details=[{"field": "file"}],
        )
    try:
        with Image.open(BytesIO(data)) as probe:
            width, height = probe.size
            if width <= 0 or height <= 0 or width * height > settings.MAX_EVIDENCE_PIXELS:
                raise AppError(
                    "Image dimensions exceed the allowed limit.",
                    code="VALIDATION_ERROR",
                    details=[{"field": "file", "max_pixels": settings.MAX_EVIDENCE_PIXELS}],
                )
            probe.verify()
        # verify() leaves the image unusable; decode a fresh handle to reject
        # truncated payloads that only fail during pixel decoding.
        with Image.open(BytesIO(data)) as decoded:
            decoded.load()
    except AppError:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise AppError(
            "File content is not a valid image.",
            code="VALIDATION_ERROR",
            details=[{"field": "file"}],
        ) from None
    return actual, width, height


def create_upload_intent(
    *, user: User, content_type: str, purpose: str, ctx: RequestContext
) -> tuple[UploadIntent, str | None, dict[str, str]]:
    if content_type not in settings.ALLOWED_EVIDENCE_CONTENT_TYPES:
        raise AppError(
            "Unsupported image type. Use JPEG, PNG or WebP.",
            details=[{"field": "content_type", "allowed": settings.ALLOWED_EVIDENCE_CONTENT_TYPES}],
        )
    try:
        purpose_enum = IntentPurpose(purpose)
    except ValueError:
        raise AppError("Unsupported upload purpose.", details=[{"field": "purpose"}]) from None
    ttl_seconds = max(1, int(settings.EVIDENCE_UPLOAD_TTL_SECONDS))
    intent = UploadIntent.objects.create(
        user=user,
        purpose=purpose_enum,
        content_type=content_type,
        max_bytes=settings.MAX_EVIDENCE_UPLOAD_BYTES,
        expires_at=timezone.now() + timedelta(seconds=ttl_seconds),
        storage_key=opaque_object_key("evidence"),
    )
    storage = get_storage_service()
    storage_key = intent.storage_key
    assert storage_key is not None  # generated above; assertion narrows for callers/tools
    upload_url = storage.presigned_put(
        storage_key, content_type, settings.MAX_EVIDENCE_UPLOAD_BYTES, expires_in=ttl_seconds
    )
    upload_headers = storage.upload_headers(content_type)
    record_audit(
        actor=user,
        action="evidence.upload_intent_created",
        target_type="upload_intent",
        target_id=intent.id,
        details={"content_type": content_type},
        ctx=ctx,
    )
    return intent, upload_url, upload_headers


def store_intent_upload(*, intent: UploadIntent, data: bytes, content_type: str) -> None:
    if intent.consumed_at is not None:
        raise AppError("This upload was already completed.", code="DUPLICATE", status_code=409)
    if intent.expires_at < timezone.now():
        raise AppError(
            "This upload window has expired; start the submission again.",
            code="VALIDATION_ERROR",
            status_code=400,
        )
    if len(data) > intent.max_bytes:
        raise AppError("Image exceeds the maximum allowed size.", details=[{"field": "file"}])
    actual, _width, _height = validate_image_bytes(data)
    if actual != intent.content_type:
        raise AppError(
            "File content does not match the declared image type.",
            code="VALIDATION_ERROR",
            details=[{"field": "file"}],
        )
    storage = get_storage_service()
    assert intent.storage_key
    storage.put_object(intent.storage_key, data, actual)
    intent.received_bytes = len(data)
    intent.received_sha256_hex = digest_bytes_sha256_hex(data)
    intent.save(update_fields=["received_bytes", "received_sha256_hex", "updated_at"])


def finalize_intent_upload(
    *, intent: UploadIntent, ctx: RequestContext | None = None
) -> tuple[UploadIntent, bool]:
    """Verify a completed local or direct-to-S3 upload and persist its digest.

    Direct S3 uploads never pass through Django, so the API must inspect the
    object before it can be evidence. This is safe to call repeatedly; the
    returned boolean indicates whether verification completed on this call.
    """
    if intent.consumed_at is not None:
        raise AppError("This upload was already used.", code="DUPLICATE", status_code=409)
    if intent.expires_at < timezone.now():
        raise AppError(
            "This upload window has expired; start the submission again.",
            code="VALIDATION_ERROR",
            status_code=400,
        )
    if intent.storage_key is None:
        raise AppError("Upload intent has no storage key.", code="VALIDATION_ERROR")
    if intent.received_sha256_hex is not None:
        return intent, False

    storage = get_storage_service()
    stat = storage.stat_object(intent.storage_key)
    if stat.size_bytes > intent.max_bytes:
        raise AppError("Image exceeds the maximum allowed size.", details=[{"field": "file"}])
    data = storage.get_object(intent.storage_key, max_bytes=intent.max_bytes)
    if len(data) > intent.max_bytes:
        raise AppError("Image exceeds the maximum allowed size.", details=[{"field": "file"}])
    actual, _width, _height = validate_image_bytes(data)
    if actual != intent.content_type:
        raise AppError(
            "File content does not match the declared image type.",
            code="VALIDATION_ERROR",
            details=[{"field": "file"}],
        )
    sha_hex = digest_bytes_sha256_hex(data)
    intent.received_bytes = len(data)
    intent.received_sha256_hex = sha_hex
    intent.save(update_fields=["received_bytes", "received_sha256_hex", "updated_at"])
    if ctx is not None:
        record_audit(
            actor=intent.user,
            action="evidence.upload_completed",
            target_type="upload_intent",
            target_id=intent.id,
            details={"size_bytes": len(data), "sha256_hex": sha_hex, "content_type": actual},
            ctx=ctx,
        )
    return intent, True


def _exif_gps_dict(exif: Any) -> dict[str, Any]:
    gps_info = exif.get_ifd(0x8825) if hasattr(exif, "get_ifd") else {}
    result: dict[str, Any] = {}
    for key, value in (gps_info or {}).items():
        result[GPSTAGS.get(key, key)] = value
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
    try:
        image = Image.open(BytesIO(data))
        exif = image.getexif()
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
    taken_raw = exif.get(36867) or exif.get(36868)
    if taken_raw:
        try:
            out["taken_at"] = datetime.strptime(str(taken_raw), "%Y:%m:%d %H:%M:%S").replace(tzinfo=UTC)
        except ValueError:
            pass
    return out


def attach_intents_to_record(
    *,
    record: DistributionRecord,
    user: User,
    site_latitude: Any,
    site_longitude: Any,
    specs: list[dict[str, Any]],
    ctx: RequestContext,
) -> list[PhotoEvidence]:
    settings_row = settings_service_.get_or_create_settings()
    storage: StorageService = get_storage_service()
    created: list[PhotoEvidence] = []
    for spec in specs:
        raw_intent_id = spec.get("intent_id")
        capture_source = spec.get("capture_source")
        client_captured_at = spec.get("client_captured_at")
        if isinstance(raw_intent_id, uuid.UUID):
            intent_id = str(raw_intent_id)
        elif isinstance(raw_intent_id, str) and raw_intent_id:
            intent_id = raw_intent_id
        else:
            raise AppError(
                "Each evidence item must include an upload intent id.",
                details=[{"field": "evidence.intent_id"}],
            )
        if capture_source not in (
            CaptureSource.CAMERA,
            CaptureSource.FILE_PICKER,
            CaptureSource.OFFLINE_CAMERA,
        ):
            raise AppError(
                "Unsupported capture source.", details=[{"field": "evidence.capture_source"}]
            )
        intent = UploadIntent.objects.select_for_update().filter(id=intent_id).first()
        if intent is None or intent.user_id != user.id:
            raise NotFoundError("Upload intent not found.")
        if intent.consumed_at is not None:
            raise AppError("This upload was already used.", code="DUPLICATE", status_code=409)
        if intent.expires_at < timezone.now():
            raise AppError("This upload window has expired; recapture the photo.", code="VALIDATION_ERROR")
        storage_key = intent.storage_key
        if storage_key is None:
            raise AppError("The photo has not finished uploading.", code="VALIDATION_ERROR")
        if intent.received_sha256_hex is None:
            # Compatibility path for direct-to-S3 clients that upload but do
            # not call the completion endpoint. Verification happens before
            # the intent is consumed or any evidence row is created.
            try:
                intent, _completed = finalize_intent_upload(intent=intent, ctx=ctx)
            except AppError as exc:
                if exc.status_code == 404:
                    raise AppError(
                        "The photo has not finished uploading.",
                        code="VALIDATION_ERROR",
                        status_code=400,
                        details=[{"field": "evidence"}],
                    ) from None
                raise

        # Check the stored size before reading. A presigned URL holder can
        # replace the object after completion; do not let that turn into an
        # unbounded read or an oversized evidence row.
        stat = storage.stat_object(storage_key)
        if stat.size_bytes > intent.max_bytes:
            raise AppError("Image exceeds the maximum allowed size.", details=[{"field": "file"}])
        if intent.received_bytes is not None and stat.size_bytes != intent.received_bytes:
            raise ConflictError(
                "Evidence object changed after upload verification.",
                code="EVIDENCE_INTEGRITY_FAILURE",
            )
        data = storage.get_object(storage_key, max_bytes=intent.max_bytes)
        if len(data) > intent.max_bytes:
            raise AppError("Image exceeds the maximum allowed size.", details=[{"field": "file"}])
        actual_type, _width, _height = validate_image_bytes(data)
        if actual_type != intent.content_type:
            raise AppError(
                "File content does not match the declared image type.",
                code="VALIDATION_ERROR",
                details=[{"field": "file"}],
            )
        sha_hex = digest_bytes_sha256_hex(data)
        if intent.received_sha256_hex != sha_hex or intent.received_bytes != len(data):
            raise ConflictError(
                "Evidence object changed after upload verification.",
                code="EVIDENCE_INTEGRITY_FAILURE",
            )
        flags: list[str] = []
        metadata_check: dict[str, Any] = {"exif": "absent"}
        duplicate_of = None
        prior = (
            PhotoEvidence.objects.filter(sha256_hex=sha_hex, distribution_record__isnull=False)
            .order_by("server_received_at")
            .first()
        )
        if prior is not None:
            flags.append(GeoFlag.DUPLICATE_IMAGE_HASH.value)
            duplicate_of = prior

        exif = extract_exif(data)
        if exif:
            metadata_check["exif"] = "present"
            if (
                exif.get("latitude") is not None
                and record.location_latitude is not None
                and record.location_longitude is not None
            ):
                distance = geodesic_distance_m(
                    Decimal(str(exif["latitude"])),
                    Decimal(str(exif["longitude"])),
                    record.location_latitude,
                    record.location_longitude,
                )
                # Keep the comparison for audit context, but never emit a
                # location warning: approval is allowed from any recorded place.
                metadata_check["exif_vs_reported_m"] = round(distance, 1)
            if exif.get("taken_at") and record.submitted_at:
                drift = abs((exif["taken_at"] - record.submitted_at).total_seconds())
                metadata_check["capture_time_drift_s"] = drift
                if drift > settings_row.max_capture_time_drift_seconds:
                    flags.append(GeoFlag.CAPTURE_TIME_MISMATCH.value)

        if client_captured_at and record.submitted_at:
            captured = (
                client_captured_at
                if client_captured_at.tzinfo
                else client_captured_at.replace(tzinfo=UTC)
            )
            drift = abs((captured - record.submitted_at).total_seconds())
            if drift > settings_row.max_capture_time_drift_seconds:
                if GeoFlag.CAPTURE_TIME_MISMATCH.value not in flags:
                    flags.append(GeoFlag.CAPTURE_TIME_MISMATCH.value)

        evidence = PhotoEvidence.objects.create(
            distribution_record=record,
            uploader_user=user,
            storage_key=storage_key,
            content_type=actual_type,
            size_bytes=len(data),
            sha256_hex=sha_hex,
            capture_source=CaptureSource(capture_source),
            client_captured_at=client_captured_at,
            server_received_at=timezone.now(),
            exif_latitude=Decimal(str(exif["latitude"])) if exif.get("latitude") is not None else None,
            exif_longitude=Decimal(str(exif["longitude"])) if exif.get("longitude") is not None else None,
            exif_taken_at=exif.get("taken_at"),
            metadata_check_result=metadata_check,
            validation_flags=flags,
            duplicate_of=duplicate_of,
            lifecycle_status=EvidenceLifecycle.ACTIVE,
        )
        intent.consumed_at = timezone.now()
        intent.save(update_fields=["consumed_at", "updated_at"])
        created.append(evidence)
    return created


def issue_view_url(*, user: User, evidence_id: uuid.UUID, ctx: RequestContext) -> dict[str, Any]:
    evidence = PhotoEvidence.objects.filter(id=evidence_id).first()
    if evidence is None:
        raise NotFoundError("Evidence not found.")
    if user.role != "ADMIN" and evidence.uploader_user_id != user.id:
        raise NotFoundError("Evidence not found.")
    storage = get_storage_service()
    url = storage.presigned_get(evidence.storage_key, str(evidence.id))
    record_audit(
        actor=user,
        action="evidence.signed_url_issued",
        target_type="photo_evidence",
        target_id=evidence.id,
        details={"ttl_seconds": settings.STORAGE_SIGNED_URL_TTL_SECONDS},
        ctx=ctx,
    )
    return {
        "evidence_id": evidence.id,
        "url": url,
        "expires_in_seconds": settings.STORAGE_SIGNED_URL_TTL_SECONDS,
    }


def load_evidence_bytes(*, evidence_id: uuid.UUID) -> tuple[bytes, str]:
    evidence = PhotoEvidence.objects.filter(id=evidence_id).first()
    if evidence is None:
        raise NotFoundError("Evidence not found.")
    storage = get_storage_service()
    stat = storage.stat_object(evidence.storage_key)
    if stat.size_bytes != evidence.size_bytes:
        raise ConflictError(
            "Evidence object changed after upload verification.",
            code="EVIDENCE_INTEGRITY_FAILURE",
        )
    data = storage.get_object(evidence.storage_key, max_bytes=evidence.size_bytes)
    if len(data) != evidence.size_bytes:
        raise ConflictError(
            "Evidence object changed after upload verification.",
            code="EVIDENCE_INTEGRITY_FAILURE",
        )
    if digest_bytes_sha256_hex(data) != evidence.sha256_hex:
        raise ConflictError(
            "Evidence object changed after upload verification.",
            code="EVIDENCE_INTEGRITY_FAILURE",
        )
    return data, evidence.content_type
