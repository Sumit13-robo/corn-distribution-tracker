"""Distribution (delivery) schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ApiModel


class EvidenceSpecIn(BaseModel):
    intent_id: uuid.UUID
    capture_source: str = Field(max_length=20)
    client_captured_at: datetime | None = None


class LocationIn(BaseModel):
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    accuracy_m: Decimal | None = None
    timestamp: datetime | None = None
    device_time: datetime | None = None
    client_created_at: datetime | None = None


class DeliveryCreateIn(BaseModel):
    assignment_id: uuid.UUID
    quantity: Decimal = Field(gt=0)
    unit: str = Field(default="KG", max_length=10)
    notes: str | None = Field(default=None, max_length=2000)
    evidence: list[EvidenceSpecIn] = Field(min_length=1, max_length=5)
    location: LocationIn | None = None

    @model_validator(mode="after")
    def _location_pair(self) -> DeliveryCreateIn:
        loc = self.location
        if loc is not None:
            has_lat = loc.latitude is not None
            has_lng = loc.longitude is not None
            if has_lat != has_lng:
                raise ValueError("location requires both latitude and longitude (or neither)")
        return self


class ApprovalIn(BaseModel):
    exception_reason: str | None = Field(default=None, max_length=2000)
    review_note: str | None = Field(default=None, max_length=2000)


class RejectIn(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class CancelIn(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class EvidenceOut(ApiModel):
    id: uuid.UUID
    content_type: str
    size_bytes: int
    sha256_hex: str
    capture_source: str
    client_captured_at: datetime | None = None
    server_received_at: datetime | None = None
    exif_latitude: Decimal | None = None
    exif_longitude: Decimal | None = None
    exif_taken_at: datetime | None = None
    metadata_check_result: dict = {}
    validation_flags: list = []
    lifecycle_status: str


class DistributionOut(ApiModel):
    id: uuid.UUID
    campaign_id: uuid.UUID | None = None
    assignment_id: uuid.UUID
    site_id: uuid.UUID
    distributor_user_id: uuid.UUID
    quantity_kg: Decimal
    status: str
    client_created_at: datetime | None = None
    submitted_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by: uuid.UUID | None = None
    review_reason: str | None = None
    review_exception_reason: str | None = None
    stock_movement_id: uuid.UUID | None = None
    notes: str | None = None
    location_latitude: Decimal | None = None
    location_longitude: Decimal | None = None
    location_accuracy_m: Decimal | None = None
    location_timestamp: datetime | None = None
    device_reported_location_time: datetime | None = None
    distance_to_site_m: Decimal | None = None
    geo_status: str
    geo_flags: list = []
    evidence: list[EvidenceOut] = []
    created_at: datetime
    updated_at: datetime | None = None
