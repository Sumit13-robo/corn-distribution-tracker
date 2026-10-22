"""Inventory schemas: quantities are decimals serialized as strings."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel


class ReceiptIn(ApiModel):
    quantity: Decimal = Field(gt=0)
    unit: str = Field(default="KG", max_length=10)
    source_reference: str = Field(min_length=1, max_length=200)
    received_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=1000)


class AllocationIn(ApiModel):
    distributor_user_id: uuid.UUID
    quantity: Decimal = Field(gt=0)
    unit: str = Field(default="KG", max_length=10)
    campaign_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=1000)


class AdjustmentIn(ApiModel):
    account_id: uuid.UUID
    quantity: Decimal = Field(gt=0)
    unit: str = Field(default="KG", max_length=10)
    movement_type: Literal["LOSS", "RETURN"] = "LOSS"
    reason: str = Field(min_length=3, max_length=2000)
    destination_account_id: uuid.UUID | None = None


class ReversalIn(ApiModel):
    reason: str = Field(min_length=3, max_length=2000)


class AccountOut(ApiModel):
    id: uuid.UUID
    account_type: str
    name: str
    owner_user_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    posted_balance_kg: Decimal
    reserved_kg: Decimal
    available_kg: Decimal


class MovementOut(ApiModel):
    id: uuid.UUID
    movement_type: str
    source_account_id: uuid.UUID | None = None
    destination_account_id: uuid.UUID | None = None
    quantity_kg: Decimal
    reference_type: str
    reference_id: uuid.UUID | None = None
    idempotency_key: str | None = None
    occurred_at: datetime | None = None
    posted_at: datetime
    created_by: uuid.UUID | None = None
    reason: str | None = None
    reversal_of_id: uuid.UUID | None = None
    movement_metadata: dict = {}


class ReconciliationOut(ApiModel):
    received_kg: Decimal
    loss_kg: Decimal
    sum_account_balances_kg: Decimal
    balanced: bool


class DisplayUnitOut(ApiModel):
    quantity_kg: Decimal
    unit: str
    factor_label: str
    display_value: Decimal
