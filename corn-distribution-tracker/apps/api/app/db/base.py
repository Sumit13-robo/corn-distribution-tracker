"""Type-safe declarative base with naming conventions and shared column helpers."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, MetaData, Numeric
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

convention_metadata = MetaData(naming_convention=naming_convention)


class Base(DeclarativeBase):
    """Shared declarative base; the full registry is re-exported by app.db.base."""

    metadata = convention_metadata

    def to_audit_row(self) -> dict[str, Any]:
        """A JSON-safe dict of this row's column values for audit summaries (no secrets)."""
        return json.loads(
            json.dumps({c.name: getattr(self, c.name) for c in self.__table__.columns}, default=str)
        )


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


def kg_quantity() -> Mapped[Decimal]:
    """Canonical quantity column: decimal kg with gram precision (docs/INVENTORY_LEDGER)."""
    return mapped_column(Numeric(14, 3), nullable=False)


def latitude_column() -> Mapped[Decimal]:
    return mapped_column(Numeric(9, 6), nullable=False)


def longitude_column() -> Mapped[Decimal]:
    return mapped_column(Numeric(10, 6), nullable=False)


class TimestampMixin:
    """created_at/updated_at in UTC; comparisons use UTC per docs/DOMAIN_MODEL.md."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default="now()", server_onupdate=None, nullable=True
    )
