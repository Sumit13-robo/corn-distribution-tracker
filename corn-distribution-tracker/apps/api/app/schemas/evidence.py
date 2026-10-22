"""Evidence schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UploadIntentIn(BaseModel):
    content_type: str = Field(max_length=64)
    purpose: str = Field(default="DISTRIBUTION_EVIDENCE", max_length=32)


class UploadIntentOut(BaseModel):
    intent_id: uuid.UUID
    expires_at: datetime
    upload_method: str
    upload_url: str
    headers: dict = {}


class ViewURLOut(BaseModel):
    evidence_id: uuid.UUID
    url: str
    expires_in_seconds: int
