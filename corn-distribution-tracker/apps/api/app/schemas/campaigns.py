"""Campaign schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel


class CampaignIn(ApiModel):
    name: str = Field(min_length=1, max_length=160)
    reference_code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: Literal["DRAFT", "ACTIVE", "PAUSED", "CLOSED"] = "DRAFT"
    timezone: str = Field(default="UTC", max_length=64)
    notes: str | None = Field(default=None, max_length=2000)


class CampaignPatchIn(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: Literal["DRAFT", "ACTIVE", "PAUSED", "CLOSED"] | None = None
    timezone: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=2000)


class CampaignOut(ApiModel):
    id: uuid.UUID
    name: str
    reference_code: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: str
    timezone: str
    notes: str | None = None
    created_at: datetime
