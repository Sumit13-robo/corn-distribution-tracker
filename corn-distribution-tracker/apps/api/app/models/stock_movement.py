"""Append-only stock ledger.

Doubles are never used for quantities (docs/DOMAIN_MODEL.md): canonical kg NUMERIC.
One posted movement row represents both sides (source debit + destination credit).
The partial unique index on `distribution_reference_id` guarantees exactly one
DELIVERY movement per approved distribution record (idempotent approval).
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
    Text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, uuid_pk
from app.models.enums import MovementType


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint("quantity_kg > 0", name="movement_quantity_positive"),
        # Semantics encoded as implications so rows of other types pass
        # (a plain `type='LOST' AND ...` conjunction would reject them all).
        CheckConstraint(
            "(movement_type <> 'RECEIPT' OR "
            "(source_account_id IS NULL AND destination_account_id IS NOT NULL))",
            name="receipt_semantics",
        ),
        CheckConstraint(
            "(movement_type <> 'LOSS' OR (source_account_id IS NOT NULL AND destination_account_id IS NULL))",
            name="loss_semantics",
        ),
        CheckConstraint(
            # REVERSAL is handled separately: it mirrors the reversed movement's
            # side-ness (source-only when undoing a RECEIPT, destination-only
            # when undoing a LOSS).
            "(movement_type NOT IN ('TRANSFER', 'DELIVERY', 'RETURN', 'ADJUSTMENT') OR "
            "(source_account_id IS NOT NULL AND destination_account_id IS NOT NULL "
            "AND source_account_id <> destination_account_id))",
            name="transfer_semantics",
        ),
        CheckConstraint(
            "(movement_type <> 'REVERSAL' OR "
            "(source_account_id IS NOT NULL OR destination_account_id IS NOT NULL))",
            name="reversal_semantics",
        ),
        Index(
            "uq_movement_delivery_reference",
            "distribution_reference_id",
            unique=True,
            postgresql_where=None,
        ),
        Index("ix_stock_movements_destination", "destination_account_id"),
        Index("ix_stock_movements_source", "source_account_id"),
        Index("ix_stock_movements_idempotency", "idempotency_key", unique=True),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    movement_type: Mapped[MovementType] = mapped_column(
        Enum(MovementType, native_enum=False, length=20, name="movement_type"), nullable=False
    )
    source_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("inventory_accounts.id"))
    destination_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("inventory_accounts.id"))
    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    # What produced the movement: distribution_record | admin_operation | system_bootstrap
    reference_type: Mapped[str] = mapped_column(String(40), nullable=False)
    reference_id: Mapped[uuid.UUID | None] = mapped_column()
    # Exactly one DELIVERY movement may reference an approved distribution record.
    distribution_reference_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("distribution_records.id"))
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    posted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reason: Mapped[str | None] = mapped_column(Text)
    reversal_of_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stock_movements.id", ondelete="RESTRICT"), unique=True
    )
    movement_metadata: Mapped[dict | None] = mapped_column(postgresql.JSONB, default=dict)
