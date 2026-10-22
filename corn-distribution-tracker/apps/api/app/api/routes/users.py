"""Admin routes for distributor accounts; invitations/deactivation flows roll up here."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import AdminDep, PaginationDep, RequestCtx, get_db
from app.core.errors import NotFoundError
from app.models import DistributorAssignment, Invitation, StockAccount, User
from app.schemas.users import DistributorDetailOut, DistributorOut, DistributorUpdateIn
from app.services import auth_service, inventory_service
from app.services.audit_service import record_audit

DbDep = Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/admin", tags=["users"])


class DistributorListOut(BaseModel):
    items: list[DistributorDetailOut]
    total: int
    limit: int
    offset: int


@router.get("/distributors", response_model=DistributorListOut)
def list_distributors(
    admin: AdminDep,
    db: DbDep,
    pagination: PaginationDep,
    search: str | None = Query(default=None, max_length=120),
):
    stmt = select(User).where(User.role == "DISTRIBUTOR")
    if search:
        stmt = stmt.where(User.display_name.ilike(f"%{search}%") | User.email_normalized.ilike(f"%{search}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    users = list(
        db.scalars(stmt.order_by(User.created_at.desc()).limit(pagination.limit).offset(pagination.offset))
    )
    items: list[DistributorDetailOut] = []
    for user in users:
        stock = _user_stock(db, user)
        open_assignments = (
            db.scalar(
                select(func.count())
                .select_from(DistributorAssignment)
                .where(
                    DistributorAssignment.distributor_user_id == user.id,
                    DistributorAssignment.status.in_(["ACTIVE", "PAUSED"]),
                )
            )
            or 0
        )
        assigned_campaigns = (
            db.scalar(
                select(func.count(func.distinct(DistributorAssignment.campaign_id))).where(
                    DistributorAssignment.distributor_user_id == user.id
                )
            )
            or 0
        )
        open_invite = (
            db.scalar(
                select(func.count())
                .select_from(Invitation)
                .where(
                    Invitation.email_normalized == user.email_normalized,
                    Invitation.accepted_at.is_(None),
                    Invitation.revoked_at.is_(None),
                    Invitation.expires_at > func.now(),
                )
            )
            or 0
        )
        items.append(
            DistributorDetailOut(
                id=user.id,
                email=user.email_normalized,
                display_name=user.display_name,
                is_active=user.is_active,
                must_reset_password=user.must_reset_password,
                last_login_at=user.last_login_at,
                created_at=user.created_at,
                stock_balance_kg=str(stock["balance"]),
                reserved_kg=str(stock["reserved"]),
                available_kg=str(stock["available"]),
                assigned_campaign_count=int(assigned_campaigns),
                open_assignment_count=int(open_assignments),
                has_open_invitation=int(open_invite) > 0,
            )
        )
    return DistributorListOut(items=items, total=int(total), limit=pagination.limit, offset=pagination.offset)


@router.get("/distributors/{user_id}", response_model=DistributorDetailOut)
def get_distributor(user_id: uuid.UUID, admin: AdminDep, db: DbDep):
    user = db.get(User, user_id)
    if user is None or user.role != "DISTRIBUTOR":
        raise NotFoundError("Distributor not found.")
    stock = _user_stock(db, user)
    return DistributorDetailOut(
        id=user.id,
        email=user.email_normalized,
        display_name=user.display_name,
        is_active=user.is_active,
        must_reset_password=user.must_reset_password,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        stock_balance_kg=str(stock["balance"]),
        reserved_kg=str(stock["reserved"]),
        available_kg=str(stock["available"]),
    )


@router.patch("/distributors/{user_id}", response_model=DistributorDetailOut)
def update_distributor(
    user_id: uuid.UUID,
    payload: DistributorUpdateIn,
    admin: AdminDep,
    db: DbDep,
    ctx: RequestCtx,
):
    user = db.get(User, user_id)
    if user is None or user.role != "DISTRIBUTOR":
        raise NotFoundError("Distributor not found.")
    if payload.display_name:
        user.display_name = payload.display_name
    record_audit(
        db,
        actor=admin.user,
        action="user.updated",
        target_type="user",
        target_id=user.id,
        details={"changed_fields": list(payload.model_dump(exclude_unset=True).keys())},
        ctx=ctx,
    )
    db.commit()
    stock = _user_stock(db, user)
    return DistributorDetailOut(
        id=user.id,
        email=user.email_normalized,
        display_name=user.display_name,
        is_active=user.is_active,
        must_reset_password=user.must_reset_password,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        stock_balance_kg=str(stock["balance"]),
        reserved_kg=str(stock["reserved"]),
        available_kg=str(stock["available"]),
        open_assignment_count=int(
            db.scalar(
                select(func.count())
                .select_from(DistributorAssignment)
                .where(
                    DistributorAssignment.distributor_user_id == user.id,
                    DistributorAssignment.status.in_(["ACTIVE", "PAUSED"]),
                )
            )
            or 0
        ),
    )


@router.post("/distributors/{user_id}/deactivate", response_model=DistributorOut)
def deactivate_distributor(user_id: uuid.UUID, admin: AdminDep, db: DbDep, ctx: RequestCtx):
    user = db.get(User, user_id)
    if user is None or user.role != "DISTRIBUTOR":
        raise NotFoundError("Distributor not found.")
    auth_service.deactivate_user(db, admin=admin.user, target=user, ctx=ctx)
    db.commit()
    return DistributorOut(
        id=user.id,
        email=user.email_normalized,
        display_name=user.display_name,
        is_active=user.is_active,
        must_reset_password=user.must_reset_password,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


def _user_stock(db: Session, user: User) -> dict[str, Decimal]:
    account = db.scalar(select(StockAccount).where(StockAccount.owner_user_id == user.id))
    if account is None:
        return {"balance": Decimal(0), "reserved": Decimal(0), "available": Decimal(0)}
    balance = inventory_service.posted_balance_kg(db, account.id)
    reserved = inventory_service.reserved_kg(db, user.id)
    return {"balance": balance, "reserved": reserved, "available": balance - reserved}
