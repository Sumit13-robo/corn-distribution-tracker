"""Assignment schemas (admin management + distributor self-service reads)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel
from app.schemas.sites import SiteOut


class AssignmentIn(ApiModel):
    site_id: uuid.UUID
    campaign_id: uuid.UUID | None = None
    distributor_user_id: uuid.UUID
    target_quantity: Decimal = Field(gt=0)
    unit: str = Field(default="KG", max_length=10)
    due_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=1000)


class AssignmentPatchIn(ApiModel):
    target_quantity: Decimal | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, max_length=10)
    due_at: datetime | None = None
    status: Literal["ACTIVE", "PAUSED", "COMPLETE"] | None = None
    notes: str | None = Field(default=None, max_length=1000)


class AssignmentOut(ApiModel):
    id: uuid.UUID
    campaign_id: uuid.UUID | None = None
    site_id: uuid.UUID
    distributor_user_id: uuid.UUID
    target_quantity_kg: Decimal
    due_at: datetime | None = None
    status: str
    notes: str | None = None
    created_at: datetime


class DistributorAssignmentItemOut(ApiModel):
    assignment_id: uuid.UUID
    campaign_id: uuid.UUID | None = None
    due_at: datetime | None = None
    status: str
    target_kg: Decimal
    approved_kg: Decimal
    pending_kg: Decimal
    remaining_target_kg: Decimal
    over_target_kg: Decimal
    site: SiteOut | None = None
