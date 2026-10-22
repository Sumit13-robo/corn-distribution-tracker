"""Inventory ledger domain service.

Rules (docs/architecture/INVENTORY_LEDGER.md):
- One posted movement row represents both sides: exactly one source loses and one
  destination gains the same quantity. Balances are always derived from movements.
- Pending (SUBMITTED) distribution records are reservations, never postings.
- All mutations run inside the caller's transaction; account rows are locked with
  SELECT ... FOR UPDATE (ordered by id) to serialize concurrent spend.
- Idempotency keys are unique; retries return the original movement.
- Movements are append-only (DB triggers in the migration also block UPDATE/DELETE).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.units import convert_to_kg
from app.models import (
    AccountType,
    DistributionRecord,
    MovementType,
    RecordStatus,
    StockAccount,
    StockMovement,
    User,
)
from app.services import settings_service
from app.services.audit_service import RequestContext, record_audit

AccountScope = Literal["all", "own"]


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------


def get_central_account(db: Session) -> StockAccount:
    central = db.scalar(select(StockAccount).where(StockAccount.account_type == AccountType.CENTRAL))
    if central is None:
        raise AppError("Central account is not bootstrapped.", code="INTERNAL_ERROR", status_code=500)
    return central


def get_or_create_distributor_account(db: Session, user: User) -> StockAccount:
    account = db.scalar(select(StockAccount).where(StockAccount.owner_user_id == user.id))
    if account is None:
        account = StockAccount(
            account_type=AccountType.DISTRIBUTOR, owner_user_id=user.id, name=f"Stock: {user.display_name}"
        )
        db.add(account)
        db.flush()
    return account


def get_or_create_site_account(db: Session, site_id: uuid.UUID) -> StockAccount:
    account = db.scalar(select(StockAccount).where(StockAccount.site_id == site_id))
    if account is None:
        account = StockAccount(
            account_type=AccountType.SITE, site_id=site_id, name=f"Site account {str(site_id)[:8]}"
        )
        db.add(account)
        db.flush()
    return account


def lock_accounts(db: Session, *account_ids: uuid.UUID) -> list[StockAccount]:
    """Lock account rows in deterministic (id) order to avoid deadlocks."""
    ids = sorted(set(account_ids))
    rows = list(
        db.scalars(
            select(StockAccount).where(StockAccount.id.in_(ids)).order_by(StockAccount.id).with_for_update()
        )
    )
    return rows


# ---------------------------------------------------------------------------
# Balances (always ledger-derived; never an editable field)
# ---------------------------------------------------------------------------


def posted_balance_kg(db: Session, account_id: uuid.UUID) -> Decimal:
    inflow = db.scalar(
        select(func.coalesce(func.sum(StockMovement.quantity_kg), 0)).where(
            StockMovement.destination_account_id == account_id
        )
    ) or Decimal(0)
    outflow = db.scalar(
        select(func.coalesce(func.sum(StockMovement.quantity_kg), 0)).where(
            StockMovement.source_account_id == account_id
        )
    ) or Decimal(0)
    return Decimal(inflow) - Decimal(outflow)


def reserved_kg(db: Session, distributor_user_id: uuid.UUID) -> Decimal:
    """Sum of open SUBMITTED distribution records for this distributor (reservations)."""
    total = db.scalar(
        select(func.coalesce(func.sum(DistributionRecord.quantity_kg), 0)).where(
            DistributionRecord.distributor_user_id == distributor_user_id,
            DistributionRecord.status == RecordStatus.SUBMITTED,
        )
    ) or Decimal(0)
    return Decimal(total)


def available_kg(
    db: Session, account: StockAccount, *, distributor_user_id: uuid.UUID | None = None
) -> Decimal:
    balance = posted_balance_kg(db, account.id)
    reserved = reserved_kg(db, distributor_user_id) if distributor_user_id else Decimal(0)
    return balance - reserved


# ---------------------------------------------------------------------------
# Movement posting
# ---------------------------------------------------------------------------


def post_movement(
    db: Session,
    *,
    movement_type: MovementType,
    source_account_id: uuid.UUID | None,
    destination_account_id: uuid.UUID | None,
    quantity_kg: Decimal,
    reference_type: str,
    reference_id: uuid.UUID | None = None,
    distribution_reference_id: uuid.UUID | None = None,
    idempotency_key: str | None = None,
    occurred_at: datetime | None = None,
    created_by: uuid.UUID | None = None,
    reason: str | None = None,
    reversal_of_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> StockMovement:
    if quantity_kg <= 0:
        raise AppError("Movement quantity must be positive.", details=[{"field": "quantity"}])
    if idempotency_key:
        existing = db.scalar(select(StockMovement).where(StockMovement.idempotency_key == idempotency_key))
        if existing is not None:
            return existing
    movement = StockMovement(
        movement_type=movement_type,
        source_account_id=source_account_id,
        destination_account_id=destination_account_id,
        quantity_kg=quantity_kg,
        reference_type=reference_type,
        reference_id=reference_id,
        distribution_reference_id=distribution_reference_id,
        idempotency_key=idempotency_key,
        occurred_at=occurred_at or datetime.now(UTC),
        created_by=created_by,
        reason=reason,
        reversal_of_id=reversal_of_id,
        movement_metadata=metadata or {},
    )
    db.add(movement)
    db.flush()
    return movement


# ---------------------------------------------------------------------------
# Admin operations
# ---------------------------------------------------------------------------


def receive_stock(
    db: Session,
    *,
    admin: User,
    quantity: Decimal,
    unit: str,
    source_reference: str,
    received_at: datetime | None,
    notes: str | None,
    idempotency_key: str,
    ctx: RequestContext,
) -> StockMovement:
    settings_row = settings_service.get_or_create_settings(db)
    kg = convert_to_kg(quantity, unit, settings_row.kg_per_bag)
    central = get_central_account(db)
    lock_accounts(db, central.id)
    movement = post_movement(
        db,
        movement_type=MovementType.RECEIPT,
        source_account_id=None,
        destination_account_id=central.id,
        quantity_kg=kg,
        reference_type="admin_receipt",
        idempotency_key=idempotency_key,
        occurred_at=received_at,
        created_by=admin.id,
        reason=notes,
        metadata={"source_reference": source_reference},
    )
    record_audit(
        db,
        actor=admin,
        action="stock.received",
        target_type="stock_movement",
        target_id=movement.id,
        details={"quantity_kg": str(kg), "source_reference": source_reference},
        ctx=ctx,
    )
    db.flush()
    return movement


def allocate_stock(
    db: Session,
    *,
    admin: User,
    distributor_user_id: uuid.UUID,
    quantity: Decimal,
    unit: str,
    campaign_id: uuid.UUID | None,
    notes: str | None,
    idempotency_key: str,
    ctx: RequestContext,
) -> StockMovement:
    settings_row = settings_service.get_or_create_settings(db)
    kg = convert_to_kg(quantity, unit, settings_row.kg_per_bag)
    central = get_central_account(db)
    distributor_user = db.get(User, distributor_user_id)
    if distributor_user is None or distributor_user.role != "DISTRIBUTOR":
        raise NotFoundError("Distributor not found.")
    distributor_account = get_or_create_distributor_account(db, distributor_user)

    lock_accounts(db, central.id, distributor_account.id)
    available = posted_balance_kg(db, central.id)
    if kg > available:
        raise ConflictError(
            "Central stock is insufficient for this allocation.",
            code="INSUFFICIENT_STOCK",
            details=[{"available_kg": str(available)}],
        )
    movement = post_movement(
        db,
        movement_type=MovementType.TRANSFER,
        source_account_id=central.id,
        destination_account_id=distributor_account.id,
        quantity_kg=kg,
        reference_type="admin_allocation",
        idempotency_key=idempotency_key,
        created_by=admin.id,
        reason=notes,
        metadata={"campaign_id": str(campaign_id) if campaign_id else None},
    )
    record_audit(
        db,
        actor=admin,
        action="stock.allocated",
        target_type="stock_movement",
        target_id=movement.id,
        details={"distributor_user_id": str(distributor_user_id), "quantity_kg": str(kg)},
        ctx=ctx,
    )
    db.flush()
    return movement


def adjust_stock(
    db: Session,
    *,
    admin: User,
    account_id: uuid.UUID,
    quantity: Decimal,
    unit: str,
    movement_type: Literal[MovementType.LOSS, MovementType.RETURN],
    reason: str,
    destination_account_id: uuid.UUID | None,
    idempotency_key: str,
    ctx: RequestContext,
) -> StockMovement:
    if not reason or not reason.strip():
        raise AppError("A reason is required for stock adjustments.", details=[{"field": "reason"}])
    if movement_type == MovementType.RETURN and destination_account_id is None:
        raise AppError(
            "Return movements require a destination account.", details=[{"field": "destination_account_id"}]
        )
    settings_row = settings_service.get_or_create_settings(db)
    kg = convert_to_kg(quantity, unit, settings_row.kg_per_bag)
    source = db.get(StockAccount, account_id)
    if source is None:
        raise NotFoundError("Account not found.")
    lock_accounts(db, *[account_id, destination_account_id] if destination_account_id else [account_id])
    balance = posted_balance_kg(db, account_id)
    if movement_type == MovementType.LOSS and kg > balance:
        raise ConflictError(
            "Adjustment would create a negative balance.",
            code="INSUFFICIENT_STOCK",
            details=[{"available_kg": str(balance)}],
        )
    if movement_type == MovementType.RETURN and destination_account_id is not None:
        if kg > balance:
            raise ConflictError("Return would overdraw the source account.", code="INSUFFICIENT_STOCK")
        if destination_account_id == account_id:
            raise AppError("Source and destination must differ.")
    movement = post_movement(
        db,
        movement_type=MovementType(movement_type),
        source_account_id=account_id,
        destination_account_id=destination_account_id,
        quantity_kg=kg,
        reference_type="admin_adjustment",
        idempotency_key=idempotency_key,
        created_by=admin.id,
        reason=reason,
    )
    record_audit(
        db,
        actor=admin,
        action=f"stock.{movement_type.value.lower()}",
        target_type="stock_movement",
        target_id=movement.id,
        reason=reason,
        details={"quantity_kg": str(kg), "account_id": str(account_id)},
        ctx=ctx,
    )
    db.flush()
    return movement


def reverse_movement(
    db: Session,
    *,
    admin: User,
    movement_id: uuid.UUID,
    reason: str,
    idempotency_key: str,
    ctx: RequestContext,
) -> StockMovement:
    if not reason or not reason.strip():
        raise AppError("A reason is required for reversals.", details=[{"field": "reason"}])
    existing = db.scalar(select(StockMovement).where(StockMovement.idempotency_key == idempotency_key))
    if existing is not None:
        return existing
    original = db.get(StockMovement, movement_id)
    if original is None:
        raise NotFoundError("Movement not found.")
    if original.reversal_of_id is not None:
        raise ConflictError("This movement has already been reversed.", code="ILLEGAL_STATE")
    source_id = original.source_account_id
    destination_id = original.destination_account_id
    if source_id is None and destination_id is None:
        raise ConflictError("This movement cannot be reversed.", code="ILLEGAL_STATE")
    lock_accounts(db, *([x for x in (source_id, destination_id) if x is not None]))
    reversal = post_movement(
        db,
        movement_type=MovementType.REVERSAL,
        source_account_id=destination_id,
        destination_account_id=source_id,
        quantity_kg=original.quantity_kg,
        reference_type="reversal",
        reference_id=original.reference_id,
        idempotency_key=idempotency_key,
        created_by=admin.id,
        reason=reason,
        reversal_of_id=original.id,
        metadata={"reverses_movement_type": original.movement_type.value},
    )
    record_audit(
        db,
        actor=admin,
        action="stock.reversed",
        target_type="stock_movement",
        target_id=reversal.id,
        reason=reason,
        details={"reversal_of": str(original.id), "quantity_kg": str(original.quantity_kg)},
        ctx=ctx,
    )
    db.flush()
    return reversal


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------


def account_summaries(db: Session, *, scope_user: User | None = None) -> list[dict[str, Any]]:
    stmt = select(StockAccount).order_by(StockAccount.account_type, StockAccount.created_at)
    if scope_user is not None:
        stmt = stmt.where(StockAccount.owner_user_id == scope_user.id)
    accounts = list(db.scalars(stmt))
    summaries = []
    for account in accounts:
        balance = posted_balance_kg(db, account.id)
        reserved = reserved_kg(db, account.owner_user_id) if account.owner_user_id else Decimal(0)
        summaries.append(
            {
                "id": account.id,
                "account_type": account.account_type.value,
                "name": account.name,
                "owner_user_id": account.owner_user_id,
                "site_id": account.site_id,
                "posted_balance_kg": balance,
                "reserved_kg": reserved,
                "available_kg": balance - reserved,
            }
        )
    return summaries


def reconciliation_summary(db: Session) -> dict[str, Any]:
    """Admin reconciliation: conservation check across the whole ledger."""
    by_type: dict[str, Decimal] = {}
    for row in db.execute(
        select(StockMovement.movement_type, func.sum(StockMovement.quantity_kg)).group_by(
            StockMovement.movement_type
        )
    ):
        by_type[row[0].value] = Decimal(row[1] or 0)
    received = by_type.get("RECEIPT", Decimal(0))
    losses = by_type.get("LOSS", Decimal(0))
    accounts = list(db.scalars(select(StockAccount)))
    total_balance = sum((posted_balance_kg(db, a.id) for a in accounts), Decimal(0))
    return {
        "received_kg": received,
        "loss_kg": losses,
        "sum_account_balances_kg": total_balance,
        "balanced": (received - losses) == total_balance,
    }
