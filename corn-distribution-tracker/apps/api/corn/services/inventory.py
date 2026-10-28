"""Inventory ledger domain service.

One posted movement row represents both sides (source debit + destination
credit). Balances are derived; pending SUBMITTED records are reservations.
All mutation paths lock account rows in deterministic order and execute inside
the caller's transaction.
"""

from __future__ import annotations

import hashlib
import json
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

RECEIPT_SCOPE = "inventory.receipt"
ALLOCATION_SCOPE = "inventory.allocation"
ADJUSTMENT_SCOPE = "inventory.adjustment"
REVERSAL_SCOPE = "inventory.reversal"
DELIVERY_SCOPE = "distribution.approval"


def request_fingerprint(payload: dict[str, Any]) -> str:
    """Stable SHA-256 of the business request represented by an idempotency key.

    The key alone is not enough: reusing a key for a different payload must be a
    conflict, never a silent replay of unrelated stock or delivery data.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _check_idempotent_match(
    existing: StockMovement, *, fingerprint: str | None, scope: str
) -> StockMovement:
    # Rows created before migration 0004 have no stored request fingerprint.
    # They cannot be replayed safely: fail closed and make the caller choose a
    # new key instead of returning a potentially unrelated movement.
    if not existing.idempotency_fingerprint:
        raise ConflictError(
            "This idempotency key predates payload verification; retry with a new key.",
            code="IDEMPOTENCY_CONFLICT",
            details=[{"scope": scope, "legacy": True}],
        )
    if fingerprint and existing.idempotency_fingerprint != fingerprint:
        raise ConflictError(
            "This idempotency key was already used for a different request.",
            code="IDEMPOTENCY_CONFLICT",
            details=[{"scope": scope}],
        )
    return existing


def find_idempotent_movement(
    *, scope: str, key: str | None, fingerprint: str | None = None
) -> StockMovement | None:
    if not key:
        return None
    existing = StockMovement.objects.filter(
        idempotency_scope=scope, idempotency_key=key
    ).first()
    if existing is None:
        return None
    return _check_idempotent_match(existing, fingerprint=fingerprint, scope=scope)


def get_central_account() -> StockAccount:
    central = StockAccount.objects.filter(account_type=AccountType.CENTRAL).first()
    if central is None:
        raise AppError("Central account is not bootstrapped.", code="INTERNAL_ERROR", status_code=500)
    return central


def get_or_create_distributor_account(user: User) -> StockAccount:
    account, _created = StockAccount.objects.get_or_create(
        account_type=AccountType.DISTRIBUTOR,
        owner_user=user,
        defaults={"name": f"Stock: {user.display_name}"},
    )
    return account


def get_or_create_site_account(site_id: uuid.UUID) -> StockAccount:
    account = StockAccount.objects.filter(
        account_type=AccountType.SITE, site_id=site_id
    ).first()
    if account is not None:
        return account
    site_row = DistributionSite.objects.filter(id=site_id).only("site_code").first()
    if site_row is None:
        raise ValueError("Site does not exist")
    account, _created = StockAccount.objects.get_or_create(
        account_type=AccountType.SITE,
        site_id=site_id,
        defaults={"name": f"Site stock — {site_row.site_code}"},
    )
    return account


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


def reserved_kg(
    distributor_user_id: uuid.UUID, *, exclude_record_id: uuid.UUID | None = None
) -> Decimal:
    qs = DistributionRecord.objects.filter(
        distributor_user_id=distributor_user_id, status=RecordStatus.SUBMITTED
    )
    if exclude_record_id is not None:
        qs = qs.exclude(id=exclude_record_id)
    total = qs.aggregate(total=Coalesce(Sum("quantity_kg"), ZERO))["total"] or ZERO
    return Decimal(total)


def available_kg(
    account: StockAccount,
    *,
    distributor_user_id: uuid.UUID | None = None,
    exclude_record_id: uuid.UUID | None = None,
) -> Decimal:
    balance = posted_balance_kg(account.id)
    reserved = (
        reserved_kg(distributor_user_id, exclude_record_id=exclude_record_id)
        if distributor_user_id
        else ZERO
    )
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
    idempotency_scope: str = "inventory.other",
    idempotency_key: str | None = None,
    idempotency_fingerprint: str | None = None,
    occurred_at: datetime | None = None,
    created_by: uuid.UUID | None = None,
    reason: str | None = None,
    reversal_of_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> StockMovement:
    if quantity_kg <= 0:
        raise AppError("Movement quantity must be positive.", details=[{"field": "quantity"}])
    fingerprint = idempotency_fingerprint or request_fingerprint(
        {
            "scope": idempotency_scope,
            "movement_type": movement_type,
            "source_account_id": source_account_id,
            "destination_account_id": destination_account_id,
            "quantity_kg": str(quantity_kg),
            "reference_type": reference_type,
            "reference_id": reference_id,
            "distribution_reference_id": distribution_reference_id,
            "occurred_at": occurred_at,
            "created_by": created_by,
            "reason": reason,
            "reversal_of_id": reversal_of_id,
            "metadata": metadata or {},
        }
    )
    if idempotency_key:
        existing = find_idempotent_movement(
            scope=idempotency_scope, key=idempotency_key, fingerprint=fingerprint
        )
        if existing is not None:
            return existing
        if distribution_reference_id is not None and StockMovement.objects.filter(
            distribution_reference_id=distribution_reference_id
        ).exists():
            raise ConflictError(
                "A stock movement already exists for this delivery.",
                code="ILLEGAL_STATE",
            )
        movement, created = StockMovement.objects.get_or_create(
            idempotency_scope=idempotency_scope,
            idempotency_key=idempotency_key,
            defaults={
                "movement_type": movement_type,
                "source_account_id": source_account_id,
                "destination_account_id": destination_account_id,
                "quantity_kg": quantity_kg,
                "reference_type": reference_type,
                "reference_id": reference_id,
                "distribution_reference_id": distribution_reference_id,
                "idempotency_fingerprint": fingerprint,
                "occurred_at": occurred_at or timezone.now(),
                "created_by_id": created_by,
                "reason": reason,
                "reversal_of_id": reversal_of_id,
                "movement_metadata": metadata or {},
            },
        )
        if not created:
            _check_idempotent_match(movement, fingerprint=fingerprint, scope=idempotency_scope)
        return movement
    if distribution_reference_id is not None and StockMovement.objects.filter(
        distribution_reference_id=distribution_reference_id
    ).exists():
        raise ConflictError(
            "A stock movement already exists for this delivery.",
            code="ILLEGAL_STATE",
        )
    return StockMovement.objects.create(
        movement_type=movement_type,
        source_account_id=source_account_id,
        destination_account_id=destination_account_id,
        quantity_kg=quantity_kg,
        reference_type=reference_type,
        reference_id=reference_id,
        distribution_reference_id=distribution_reference_id,
        idempotency_scope=idempotency_scope,
        idempotency_fingerprint=fingerprint,
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
    fingerprint = request_fingerprint(
        {
            "scope": RECEIPT_SCOPE,
            "actor": admin.id,
            "quantity": str(quantity),
            "unit": unit,
            "source_reference": source_reference,
            "received_at": received_at,
            "notes": notes,
        }
    )
    existing = find_idempotent_movement(
        scope=RECEIPT_SCOPE, key=idempotency_key, fingerprint=fingerprint
    )
    if existing is not None:
        return existing
    settings_row = settings_service_.get_or_create_settings()
    kg = convert_to_kg(quantity, unit, settings_row.kg_per_bag)
    central = get_central_account()
    lock_accounts(central.id)
    existing = find_idempotent_movement(
        scope=RECEIPT_SCOPE, key=idempotency_key, fingerprint=fingerprint
    )
    if existing is not None:
        return existing
    movement = post_movement(
        movement_type=MovementType.RECEIPT,
        source_account_id=None,
        destination_account_id=central.id,
        quantity_kg=kg,
        reference_type="admin_receipt",
        idempotency_scope=RECEIPT_SCOPE,
        idempotency_key=idempotency_key,
        idempotency_fingerprint=fingerprint,
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
    fingerprint = request_fingerprint(
        {
            "scope": ALLOCATION_SCOPE,
            "actor": admin.id,
            "distributor_user_id": distributor_user_id,
            "quantity": str(quantity),
            "unit": unit,
            "campaign_id": campaign_id,
            "notes": notes,
        }
    )
    existing = find_idempotent_movement(
        scope=ALLOCATION_SCOPE, key=idempotency_key, fingerprint=fingerprint
    )
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
    existing = find_idempotent_movement(
        scope=ALLOCATION_SCOPE, key=idempotency_key, fingerprint=fingerprint
    )
    if existing is not None:
        return existing
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
        idempotency_scope=ALLOCATION_SCOPE,
        idempotency_key=idempotency_key,
        idempotency_fingerprint=fingerprint,
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
    fingerprint = request_fingerprint(
        {
            "scope": ADJUSTMENT_SCOPE,
            "actor": admin.id,
            "account_id": account_id,
            "quantity": str(quantity),
            "unit": unit,
            "movement_type": movement_type,
            "reason": reason,
            "destination_account_id": destination_account_id,
        }
    )
    existing = find_idempotent_movement(
        scope=ADJUSTMENT_SCOPE, key=idempotency_key, fingerprint=fingerprint
    )
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
    existing = find_idempotent_movement(
        scope=ADJUSTMENT_SCOPE, key=idempotency_key, fingerprint=fingerprint
    )
    if existing is not None:
        return existing
    available = _available_for_debit(source)
    if movement_type == MovementType.LOSS and kg > available:
        raise ConflictError(
            "Adjustment would overdraw available stock.",
            code="INSUFFICIENT_STOCK",
            details=[{"available_kg": str(available)}],
        )
    if movement_type == MovementType.RETURN and kg > available:
        raise ConflictError(
            "Return would overdraw available stock.",
            code="INSUFFICIENT_STOCK",
            details=[{"available_kg": str(available)}],
        )
    movement = post_movement(
        movement_type=movement_type,
        source_account_id=account_id,
        destination_account_id=destination_account_id,
        quantity_kg=kg,
        reference_type="admin_adjustment",
        idempotency_scope=ADJUSTMENT_SCOPE,
        idempotency_key=idempotency_key,
        idempotency_fingerprint=fingerprint,
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


def _available_for_debit(account: StockAccount) -> Decimal:
    if account.account_type == AccountType.DISTRIBUTOR and account.owner_user_id:
        return available_kg(account, distributor_user_id=account.owner_user_id)
    return posted_balance_kg(account.id)


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
    fingerprint = request_fingerprint(
        {
            "scope": REVERSAL_SCOPE,
            "actor": admin.id,
            "movement_id": movement_id,
            "reason": reason,
        }
    )
    existing = find_idempotent_movement(
        scope=REVERSAL_SCOPE, key=idempotency_key, fingerprint=fingerprint
    )
    if existing is not None:
        return existing
    original = StockMovement.objects.select_for_update().filter(id=movement_id).first()
    if original is None:
        raise NotFoundError("Movement not found.")
    existing = find_idempotent_movement(
        scope=REVERSAL_SCOPE, key=idempotency_key, fingerprint=fingerprint
    )
    if existing is not None:
        return existing
    if original.movement_type == MovementType.REVERSAL:
        raise ConflictError(
            "Reversal movements cannot be reversed; post a new adjustment instead.",
            code="ILLEGAL_STATE",
        )
    if StockMovement.objects.filter(reversal_of=original).exists():
        raise ConflictError("This movement has already been reversed.", code="ILLEGAL_STATE")
    if original.source_account_id is None and original.destination_account_id is None:
        raise ConflictError("This movement cannot be reversed.", code="ILLEGAL_STATE")

    record = None
    if original.distribution_reference_id is not None:
        record = (
            DistributionRecord.objects.select_for_update()
            .filter(id=original.distribution_reference_id)
            .first()
        )
        if record is None:
            raise ConflictError(
                "The linked delivery record is missing.", code="ILLEGAL_STATE"
            )
        if record.status == RecordStatus.REVERSED:
            raise ConflictError("This delivery has already been reversed.", code="ILLEGAL_STATE")

    source_account_id = original.destination_account_id
    destination_account_id = original.source_account_id
    locked = {account.id: account for account in lock_accounts(source_account_id, destination_account_id)}
    if source_account_id is not None:
        debit_account = locked[source_account_id]
        available = _available_for_debit(debit_account)
        if Decimal(original.quantity_kg) > available:
            raise ConflictError(
                "Reversal would overdraw the account that received the original movement.",
                code="INSUFFICIENT_STOCK",
                details=[
                    {
                        "account_id": str(source_account_id),
                        "available_kg": str(available),
                        "required_kg": str(original.quantity_kg),
                    }
                ],
            )

    reversal = post_movement(
        movement_type=MovementType.REVERSAL,
        source_account_id=source_account_id,
        destination_account_id=destination_account_id,
        quantity_kg=original.quantity_kg,
        reference_type="reversal",
        reference_id=original.reference_id,
        idempotency_scope=REVERSAL_SCOPE,
        idempotency_key=idempotency_key,
        idempotency_fingerprint=fingerprint,
        created_by=admin.id,
        reason=reason,
        reversal_of_id=original.id,
        metadata={
            "reverses_movement_type": original.movement_type,
            "original_reference_type": original.reference_type,
        },
    )
    if record is not None:
        record.status = RecordStatus.REVERSED
        record.reversed_at = timezone.now()
        record.reversed_by = admin
        record.reversal_reason = reason
        record.save(
            update_fields=["status", "reversed_at", "reversed_by", "reversal_reason", "updated_at"]
        )
        record_audit(
            actor=admin,
            action="distribution.reversed",
            target_type="distribution_record",
            target_id=record.id,
            reason=reason,
            details={
                "reversal_movement_id": str(reversal.id),
                "original_stock_movement_id": str(original.id),
                "quantity_kg": str(original.quantity_kg),
            },
            ctx=ctx,
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

    reversed_receipts = ZERO
    reversed_losses = ZERO
    reversals = StockMovement.objects.filter(
        movement_type=MovementType.REVERSAL,
        reversal_of__isnull=False,
    ).select_related("reversal_of")
    for reversal in reversals:
        original = reversal.reversal_of
        assert original is not None
        if original.movement_type == MovementType.RECEIPT:
            reversed_receipts += Decimal(reversal.quantity_kg)
        elif original.movement_type == MovementType.LOSS:
            reversed_losses += Decimal(reversal.quantity_kg)

    net_external_kg = received - reversed_receipts - losses + reversed_losses
    # Sum all credits minus all debits in two aggregates. This is equivalent to
    # summing each derived account balance but avoids one query per account.
    total_inflow = (
        StockMovement.objects.filter(destination_account__isnull=False).aggregate(
            total=Coalesce(Sum("quantity_kg"), ZERO)
        )["total"]
        or ZERO
    )
    total_outflow = (
        StockMovement.objects.filter(source_account__isnull=False).aggregate(
            total=Coalesce(Sum("quantity_kg"), ZERO)
        )["total"]
        or ZERO
    )
    total_balance = Decimal(total_inflow) - Decimal(total_outflow)
    return {
        "received_kg": received,
        "reversed_receipt_kg": reversed_receipts,
        "loss_kg": losses,
        "reversed_loss_kg": reversed_losses,
        "net_external_kg": net_external_kg,
        "sum_account_balances_kg": total_balance,
        "balanced": net_external_kg == total_balance,
    }


def ensure_core_org_rows(*, created_by: uuid.UUID | None = None) -> StockAccount:
    settings_service_.get_or_create_settings()
    central = StockAccount.objects.filter(account_type=AccountType.CENTRAL).first()
    if central is None:
        central = StockAccount.objects.create(
            account_type=AccountType.CENTRAL, name="Central warehouse", is_active=True
        )
    return central
