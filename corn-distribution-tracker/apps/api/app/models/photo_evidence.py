"""Photo evidence metadata + upload intents.

Originals live in a private object store (opaque random keys). Evidence viewing is
authorized per-request and uses short-lived signed URLs. Content hash proves byte
identity only - never when/where an image was captured (docs/GEO_PHOTO_EVIDENCE.md).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk
from app.models.enums import (
    CaptureSource,
    EvidenceLifecycle,
    IntentPurpose,
)


class UploadIntent(TimestampMixin, Base):
    __tablename__ = "upload_intents"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    purpose: Mapped[IntentPurpose] = mapped_column(
        Enum(IntentPurpose, native_enum=False, length=32, name="intent_purpose"),
        nullable=False,
        default=IntentPurpose.DISTRIBUTION_EVIDENCE,
    )
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    max_bytes: Mapped[int] = mapped_column(nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    storage_key: Mapped[str | None] = mapped_column(String(256))
    received_bytes: Mapped[int | None] = mapped_column()
    received_sha256_hex: Mapped[str | None] = mapped_column(String(64))


class PhotoEvidence(TimestampMixin, Base):
    __tablename__ = "photo_evidence"
    __table_args__ = (
        Index("ix_photo_evidence_hash", "sha256_hex"),
        Index("ix_photo_evidence_record", "distribution_record_id"),
        CheckConstraint("size_bytes > 0", name="evidence_size_positive"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    distribution_record_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("distribution_records.id", ondelete="SET NULL")
    )
    uploader_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    thumbnail_key: Mapped[str | None] = mapped_column(String(256))
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    sha256_hex: Mapped[str] = mapped_column(String(64), nullable=False)
    capture_source: Mapped[CaptureSource] = mapped_column(
        Enum(CaptureSource, native_enum=False, length=20, name="capture_source"), nullable=False
    )
    client_captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    server_received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    # EXIF signals when the browser preserved them; absence is informational, not fraud proof.
    exif_latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    exif_longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    exif_taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_check_result: Mapped[dict] = mapped_column(postgresql.JSONB, default=dict, nullable=False)
    validation_flags: Mapped[list] = mapped_column(postgresql.JSONB, default=list, nullable=False)
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("photo_evidence.id", ondelete="SET NULL")
    )
    lifecycle_status: Mapped[EvidenceLifecycle] = mapped_column(
        Enum(EvidenceLifecycle, native_enum=False, length=20, name="evidence_lifecycle"),
        nullable=False,
        default=EvidenceLifecycle.ACTIVE,
    )
