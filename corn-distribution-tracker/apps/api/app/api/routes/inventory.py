"""Inventory routes: summary, accounts, ledger, receipts, allocations, adjustments, reversals."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import AdminDep, CurrentUserDep, PaginationDep, RequestCtx, get_db
from app.core.errors import UnprocessableEntityError
from app.models import MovementType, StockAccount
from app.schemas.common import Page, paginated
from app.schemas.inventory import (
    AccountOut,
    AdjustmentIn,
    AllocationIn,
    DisplayUnitOut,
    MovementOut,
    ReceiptIn,
    ReconciliationOut,
    ReversalIn,
)
from app.services import inventory_service, settings_service

DbDep = Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/summary")
def summary(user: CurrentUserDep, db: DbDep):
    scope_user = None if user.is_admin else user.user
    accounts = inventory_service.account_summaries(db, scope_user=scope_user)
    reconciliation = inventory_service.reconciliation_summary(db) if user.is_admin else None
    return {
        "accounts": [
            AccountOut(
                id=a["id"],
                account_type=a["account_type"],
                name=a["name"],
                owner_user_id=a["owner_user_id"],
                site_id=a["site_id"],
                posted_balance_kg=a["posted_balance_kg"],
                reserved_kg=a["reserved_kg"],
                available_kg=a["available_kg"],
            )
            for a in accounts
        ],
        "reconciliation": ReconciliationOut.model_validate(reconciliation) if reconciliation else None,
    }


@router.get("/accounts/{account_id}/ledger", response_model=Page[MovementOut])
def account_ledger(
    account_id: uuid.UUID,
    user: CurrentUserDep,
    db: DbDep,
    pagination: PaginationDep,
):
    from sqlalchemy import func

    account = db.get(StockAccount, account_id)
    if account is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("Account not found.")
    if not user.is_admin and account.owner_user_id != user.user.id:
        # A distributor may only inspect its own stock account ledger.
        raise NotFoundError("Account not found.")
    from app.models import StockMovement

    stmt = select(StockMovement).where(
        (StockMovement.source_account_id == account_id) | (StockMovement.destination_account_id == account_id)
    )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(StockMovement.posted_at.desc(), StockMovement.id.desc())
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
    )
    out = [
        MovementOut(
            id=m.id,
            movement_type=m.movement_type.value,
            source_account_id=m.source_account_id,
            destination_account_id=m.destination_account_id,
            quantity_kg=m.quantity_kg,
            reference_type=m.reference_type,
            reference_id=m.reference_id,
            idempotency_key=m.idempotency_key,
            occurred_at=m.occurred_at,
            posted_at=m.posted_at,
            created_by=m.created_by,
            reason=m.reason,
            reversal_of_id=m.reversal_of_id,
            movement_metadata=m.movement_metadata or {},
        )
        for m in rows
    ]
    return paginated(out, int(total), pagination.limit, pagination.offset)


@router.post("/receipts", response_model=MovementOut, status_code=201)
def receive_stock(
    payload: ReceiptIn,
    admin: AdminDep,
    db: DbDep,
    ctx: RequestCtx,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    movement = inventory_service.receive_stock(
        db,
        admin=admin.user,
        quantity=payload.quantity,
        unit=payload.unit,
        source_reference=payload.source_reference,
        received_at=payload.received_at,
        notes=payload.notes,
        idempotency_key=idempotency_key or f"receipt:{uuid.uuid4()}",
        ctx=ctx,
    )
    db.commit()
    return _movement_out(db, movement)


@router.post("/allocations", response_model=MovementOut, status_code=201)
def allocate_stock(
    payload: AllocationIn,
    admin: AdminDep,
    db: DbDep,
    ctx: RequestCtx,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    movement = inventory_service.allocate_stock(
        db,
        admin=admin.user,
        distributor_user_id=payload.distributor_user_id,
        quantity=payload.quantity,
        unit=payload.unit,
        campaign_id=payload.campaign_id,
        notes=payload.notes,
        idempotency_key=idempotency_key or f"allocation:{uuid.uuid4()}",
        ctx=ctx,
    )
    db.commit()
    return _movement_out(db, movement)


@router.post("/adjustments", response_model=MovementOut, status_code=201)
def adjust_stock(
    payload: AdjustmentIn,
    admin: AdminDep,
    db: DbDep,
    ctx: RequestCtx,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    movement = inventory_service.adjust_stock(
        db,
        admin=admin.user,
        account_id=payload.account_id,
        quantity=payload.quantity,
        unit=payload.unit,
        movement_type=_parse_adjustment_type(payload.movement_type),
        reason=payload.reason,
        destination_account_id=payload.destination_account_id,
        idempotency_key=idempotency_key or f"adjustment:{uuid.uuid4()}",
        ctx=ctx,
    )
    db.commit()
    return _movement_out(db, movement)


@router.post("/movements/{movement_id}/reversal", response_model=MovementOut, status_code=201)
def reverse_movement(
    movement_id: uuid.UUID,
    payload: ReversalIn,
    admin: AdminDep,
    db: DbDep,
    ctx: RequestCtx,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    movement = inventory_service.reverse_movement(
        db,
        admin=admin.user,
        movement_id=movement_id,
        reason=payload.reason,
        idempotency_key=idempotency_key or f"reversal:{uuid.uuid4()}",
        ctx=ctx,
    )
    db.commit()
    return _movement_out(db, movement)


@router.get("/display-unit", response_model=DisplayUnitOut)
def display_unit(
    user: CurrentUserDep, db: DbDep, quantity_kg: str = Query(...), unit: str | None = Query(default=None)
):
    from decimal import Decimal

    settings_row = settings_service.get_or_create_settings(db)
    display = unit or settings_row.default_display_unit.value
    from app.core.units import kg_to_display, unit_factor_label
    from app.models import DisplayUnit

    value_kg = Decimal(quantity_kg)
    shown = kg_to_display(value_kg, DisplayUnit(display), settings_row.kg_per_bag)
    return DisplayUnitOut(
        quantity_kg=value_kg,
        unit=display,
        factor_label=unit_factor_label(DisplayUnit(display), settings_row.kg_per_bag),
        display_value=shown,
    )


def _parse_adjustment_type(value: str) -> Literal[MovementType.LOSS, MovementType.RETURN]:
    """Adjustments are LOSS or RETURN only; anything else is a 422 at the boundary."""
    try:
        parsed = MovementType(value)
    except ValueError:
        raise UnprocessableEntityError(
            "movement_type must be LOSS or RETURN.",
            details=[{"field": "movement_type"}],
        ) from None
    if parsed not in (MovementType.LOSS, MovementType.RETURN):
        raise UnprocessableEntityError(
            "movement_type must be LOSS or RETURN.",
            details=[{"field": "movement_type"}],
        )
    return parsed  # the membership guard above narrows to LOSS | RETURN


def _movement_out(db: Session, movement) -> MovementOut:
    return MovementOut(
        id=movement.id,
        movement_type=movement.movement_type.value,
        source_account_id=movement.source_account_id,
        destination_account_id=movement.destination_account_id,
        quantity_kg=movement.quantity_kg,
        reference_type=movement.reference_type,
        reference_id=movement.reference_id,
        idempotency_key=movement.idempotency_key,
        occurred_at=movement.occurred_at,
        posted_at=movement.posted_at,
        created_by=movement.created_by,
        reason=movement.reason,
        reversal_of_id=movement.reversal_of_id,
        movement_metadata=movement.movement_metadata or {},
    )
