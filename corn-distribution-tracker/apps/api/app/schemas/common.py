"""Shared schema helpers. Quantities serialize as strings (JSON) to preserve decimal kg."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(ApiModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class QuantityDisplay(ApiModel):
    """Official display conversion for a canonical kg value (contract requirement)."""

    quantity_kg: Decimal
    unit: str
    factor_label: str
    display_value: Decimal


def paginated(items: list[T], total: int, limit: int, offset: int) -> Page[T]:
    return Page(items=items, total=total, limit=limit, offset=offset)


def iso(dt: datetime | None) -> datetime | None:
    """Keep tz-aware UTC timestamps (FastAPI emits ISO-8601)."""
    return dt


__all__ = ["ApiModel", "Page", "QuantityDisplay", "paginated", "iso", "uuid", "datetime", "Field", "Decimal"]
