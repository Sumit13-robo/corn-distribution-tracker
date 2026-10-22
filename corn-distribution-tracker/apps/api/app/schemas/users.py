"""Admin user/distributor schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import ApiModel


class DistributorOut(ApiModel):
    id: uuid.UUID
    email: str
    display_name: str
    is_active: bool
    must_reset_password: bool
    last_login_at: datetime | None = None
    created_at: datetime


class DistributorUpdateIn(ApiModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)


class DistributorStockOut(DistributorOut):
    stock_balance_kg: str = "0"
    reserved_kg: str = "0"
    available_kg: str = "0"


class DistributorDetailOut(DistributorStockOut):
    assigned_campaign_count: int = 0
    open_assignment_count: int = 0
    has_open_invitation: bool = False
