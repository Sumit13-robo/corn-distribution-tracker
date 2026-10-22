"""Inventory ledger domain service.

One posted movement row represents both sides (source debit + destination
credit). Balances are derived; pending SUBMITTED records are reservations.
All mutation paths lock account rows in deterministic order and execute inside
the caller's transaction.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from ..enums import AccountType, MovementType, RecordStatus
from ..errors import AppError, ConflictError, NotFoundError
from ..models import DistributionRecord, DistributionSite, StockAccount, StockMovement, User
from ..units import convert_to_kg
from . import settings as settings_service_
from .audit import RequestContext, record_audit

AccountScope = Literal["all", "own"]
ZERO = Decimal("0")


def get_central_account() -> StockAccount:
    central = StockAccount.objects.filter(account_type=AccountType.CENTRAL).first()
    if central is None:
        raise AppError("Central account is not bootstrapped.", code="INTERNAL_ERROR", status_code=500)
    return central


def get_or_create_distributor_account(user: User) -> StockAccount:
    account = StockAccount.objects.filter(owner_user=user).first()
    if account is None:
        account = StockAccount.objects.create(
            account_type=AccountType.DISTRIBUTOR,
            owner_user=user,
            name=f"Stock: {user.display_name}",
        )
    return account


def get_or_create_site_account(site_id: uuid.UUID) -> StockAccount:
    site = StockAccount.objects.filter(site_id=site_id).first()
    if site is None:
        site_row = DistributionSite.objects.filter(id=site_id).only("site_code").first()
        if site_row is None:
            raise ValueError("Site does not exist")
        site = StockAccount.objects.create(
            account_type=AccountType.SITE,
            site_id=site_id,
            name=f"Site stock — {site_row.site_code}",
        )
    return site


def lock_accounts(*account_ids: uuid.UUID | None) -> list[StockAccount]:
    ids = sorted({item for item in account_ids if item is not None})
    return list(StockAccount.objects.select_for_update().filter(id__in=ids).order_by("id"))


def posted_balance_kg(account_id: uuid.UUID) -> Decimal:
    inflow = (
        StockMovement.objects.filter(destination_account_id=account_id).aggregate(
            total=Coalesce(Sum("quantity_kg"), ZERO)
        )["total"]
        or ZERO
    )
    outflow = (
        StockMovement.objects.filter(source_account_id=account_id).aggregate(
            total=Coalesce(Sum("quantity_kg"), ZERO)
        )["total"]
        or ZERO
    )
    return Decimal(inflow) - Decimal(outflow)


def reserved_kg(distributor_user_id: uuid.UUID) -> Decimal:
    total = (
        DistributionRecord.objects.filter(
            distributor_user_id=distributor_user_id, status=RecordStatus.SUBMITTED
        ).aggregate(total=Coalesce(Sum("quantity_kg"), ZERO))["total"]
        or ZERO
    )
    return Decimal(total)


def available_kg(account: StockAccount, *, distributor_user_id: uuid.UUID | None = None) -> Decimal:
    balance = posted_balance_kg(account.id)
    reserved = reserved_kg(distributor_user_id) if distributor_user_id else ZERO
    return balance - reserved


def post_movement(
    *,
    movement_type: str,
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
        existing = StockMovement.objects.filter(idempotency_key=idempotency_key).first()
        if existing is not None:
            return existing
    return StockMovement.objects.create(
        movement_type=movement_type,
        source_account_id=source_account_id,
        destination_account_id=destination_account_id,
        quantity_kg=quantity_kg,
        reference_type=reference_type,
        reference_id=reference_id,
        distribution_reference_id=distribution_reference_id,
        idempotency_key=idempotency_key,
        occurred_at=occurred_at or timezone.now(),
        created_by_id=created_by,
        reason=reason,
        reversal_of_id=reversal_of_id,
        movement_metadata=metadata or {},
    )


def receive_stock(
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
    existing = StockMovement.objects.filter(idempotency_key=idempotency_key).first()
    if existing is not None:
        return existing
    settings_row = settings_service_.get_or_create_settings()
    kg = convert_to_kg(quantity, unit, settings_row.kg_per_bag)
    central = get_central_account()
    lock_accounts(central.id)
    movement = post_movement(
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
        actor=admin,
        action="stock.received",
        target_type="stock_movement",
        target_id=movement.id,
        details={"quantity_kg": str(kg), "source_reference": source_reference},
        ctx=ctx,
    )
    return movement


def allocate_stock(
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
    existing = StockMovement.objects.filter(idempotency_key=idempotency_key).first()
    if existing is not None:
        return existing
    settings_row = settings_service_.get_or_create_settings()
    kg = convert_to_kg(quantity, unit, settings_row.kg_per_bag)
    central = get_central_account()
    distributor_user = User.objects.filter(id=distributor_user_id, role="DISTRIBUTOR").first()
    if distributor_user is None:
        raise NotFoundError("Distributor not found.")
    if campaign_id is not None:
        from ..models import Campaign

        if not Campaign.objects.filter(id=campaign_id).exists():
            raise NotFoundError("Campaign not found.")
    distributor_account = get_or_create_distributor_account(distributor_user)
    lock_accounts(central.id, distributor_account.id)
    available = posted_balance_kg(central.id)
    if kg > available:
        raise ConflictError(
            "Central stock is insufficient for this allocation.",
            code="INSUFFICIENT_STOCK",
            details=[{"available_kg": str(available)}],
        )
    movement = post_movement(
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
        actor=admin,
        action="stock.allocated",
        target_type="stock_movement",
        target_id=movement.id,
        details={"distributor_user_id": str(distributor_user_id), "quantity_kg": str(kg)},
        ctx=ctx,
    )
    return movement


def adjust_stock(
    *,
    admin: User,
    account_id: uuid.UUID,
    quantity: Decimal,
    unit: str,
    movement_type: str,
    reason: str,
    destination_account_id: uuid.UUID | None,
    idempotency_key: str,
    ctx: RequestContext,
) -> StockMovement:
    if not reason or not reason.strip():
        raise AppError("A reason is required for stock adjustments.", details=[{"field": "reason"}])
    existing = StockMovement.objects.filter(idempotency_key=idempotency_key).first()
    if existing is not None:
        return existing
    if movement_type not in {MovementType.LOSS, MovementType.RETURN}:
        raise AppError(
            "Adjustment type must be LOSS or RETURN.", details=[{"field": "movement_type"}]
        )
    if movement_type == MovementType.RETURN and destination_account_id is None:
        raise AppError(
            "Return movements require a destination account.",
            details=[{"field": "destination_account_id"}],
        )
    if movement_type == MovementType.LOSS and destination_account_id is not None:
        raise AppError(
            "Loss movements cannot have a destination account.",
            details=[{"field": "destination_account_id"}],
        )
    settings_row = settings_service_.get_or_create_settings()
    kg = convert_to_kg(quantity, unit, settings_row.kg_per_bag)
    source = StockAccount.objects.filter(id=account_id).first()
    if source is None:
        raise NotFoundError("Account not found.")
    if destination_account_id is not None:
        destination = StockAccount.objects.filter(id=destination_account_id).first()
        if destination is None:
            raise NotFoundError("Destination account not found.")
        if destination.id == source.id:
            raise AppError("Source and destination must differ.")
    lock_accounts(account_id, destination_account_id)
    balance = posted_balance_kg(account_id)
    if movement_type == MovementType.LOSS and kg > balance:
        raise ConflictError(
            "Adjustment would create a negative balance.",
            code="INSUFFICIENT_STOCK",
            details=[{"available_kg": str(balance)}],
        )
    if movement_type == MovementType.RETURN:
        if kg > balance:
            raise ConflictError("Return would overdraw the source account.", code="INSUFFICIENT_STOCK")
    movement = post_movement(
        movement_type=movement_type,
        source_account_id=account_id,
        destination_account_id=destination_account_id,
        quantity_kg=kg,
        reference_type="admin_adjustment",
        idempotency_key=idempotency_key,
        created_by=admin.id,
        reason=reason,
    )
    record_audit(
        actor=admin,
        action=f"stock.{movement_type.lower()}",
        target_type="stock_movement",
        target_id=movement.id,
        reason=reason,
        details={"quantity_kg": str(kg), "account_id": str(account_id)},
        ctx=ctx,
    )
    return movement


def reverse_movement(
    *,
    admin: User,
    movement_id: uuid.UUID,
    reason: str,
    idempotency_key: str,
    ctx: RequestContext,
) -> StockMovement:
    if not reason or not reason.strip():
        raise AppError("A reason is required for reversals.", details=[{"field": "reason"}])
    existing = StockMovement.objects.filter(idempotency_key=idempotency_key).first()
    if existing is not None:
        return existing
    original = StockMovement.objects.filter(id=movement_id).first()
    if original is None:
        raise NotFoundError("Movement not found.")
    if StockMovement.objects.filter(reversal_of=original).exists():
        raise ConflictError("This movement has already been reversed.", code="ILLEGAL_STATE")
    if original.source_account_id is None and original.destination_account_id is None:
        raise ConflictError("This movement cannot be reversed.", code="ILLEGAL_STATE")
    lock_accounts(original.source_account_id, original.destination_account_id)
    reversal = post_movement(
        movement_type=MovementType.REVERSAL,
        source_account_id=original.destination_account_id,
        destination_account_id=original.source_account_id,
        quantity_kg=original.quantity_kg,
        reference_type="reversal",
        reference_id=original.reference_id,
        idempotency_key=idempotency_key,
        created_by=admin.id,
        reason=reason,
        reversal_of_id=original.id,
        metadata={"reverses_movement_type": original.movement_type},
    )
    record_audit(
        actor=admin,
        action="stock.reversed",
        target_type="stock_movement",
        target_id=reversal.id,
        reason=reason,
        details={"reversal_of": str(original.id), "quantity_kg": str(original.quantity_kg)},
        ctx=ctx,
    )
    return reversal


def account_summaries(*, scope_user: User | None = None) -> list[dict[str, Any]]:
    accounts = StockAccount.objects.order_by("account_type", "created_at")
    if scope_user is not None:
        accounts = accounts.filter(owner_user=scope_user)
    out: list[dict[str, Any]] = []
    for account in accounts:
        balance = posted_balance_kg(account.id)
        reserved = reserved_kg(account.owner_user_id) if account.owner_user_id else ZERO
        out.append(
            {
                "id": account.id,
                "account_type": account.account_type,
                "name": account.name,
                "owner_user_id": account.owner_user_id,
                "site_id": account.site_id,
                "posted_balance_kg": balance,
                "reserved_kg": reserved,
                "available_kg": balance - reserved,
            }
        )
    return out


def reconciliation_summary() -> dict[str, Any]:
    by_type: dict[str, Decimal] = {}
    for row in StockMovement.objects.values("movement_type").annotate(total=Sum("quantity_kg")):
        by_type[row["movement_type"]] = Decimal(row["total"] or 0)
    received = by_type.get(MovementType.RECEIPT, ZERO)
    losses = by_type.get(MovementType.LOSS, ZERO)
    total_balance = sum(
        (posted_balance_kg(account.id) for account in StockAccount.objects.all()), ZERO
    )
    return {
        "received_kg": received,
        "loss_kg": losses,
        "sum_account_balances_kg": total_balance,
        "balanced": (received - losses) == total_balance,
    }


def ensure_core_org_rows(*, created_by: uuid.UUID | None = None) -> StockAccount:
    settings_service_.get_or_create_settings()
    central = StockAccount.objects.filter(account_type=AccountType.CENTRAL).first()
    if central is None:
        central = StockAccount.objects.create(
            account_type=AccountType.CENTRAL, name="Central warehouse", is_active=True
        )
    return central
