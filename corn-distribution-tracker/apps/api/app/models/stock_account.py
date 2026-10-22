"""Inventory accounts: central warehouse, distributor stock account, site account."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk
from app.models.enums import AccountType


class StockAccount(TimestampMixin, Base):
    __tablename__ = "inventory_accounts"

    id: Mapped[uuid.UUID] = uuid_pk()
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, native_enum=False, length=20, name="account_type"), nullable=False
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    site_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("distribution_sites.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        # Exactly one central account; one distributor account per user; one site account per site.
        # (Partial unique indexes - full-table uniqueness would allow only one row per type.)
        Index(
            "uq_central_account",
            "account_type",
            unique=True,
            postgresql_where=sa_text("account_type = 'CENTRAL'"),
        ),
        Index(
            "uq_distributor_account",
            "owner_user_id",
            unique=True,
            postgresql_where=sa_text("account_type = 'DISTRIBUTOR' AND owner_user_id IS NOT NULL"),
        ),
        Index(
            "uq_site_account",
            "site_id",
            unique=True,
            postgresql_where=sa_text("account_type = 'SITE' AND site_id IS NOT NULL"),
        ),
    )
