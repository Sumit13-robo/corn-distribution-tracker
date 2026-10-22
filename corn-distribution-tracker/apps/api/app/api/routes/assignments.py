"""Assignment routes: admin management + distributor self-service list."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import AdminDep, CurrentUserDep, PaginationDep, RequestCtx, get_db
from app.schemas.assignments import (
    AssignmentIn,
    AssignmentOut,
    AssignmentPatchIn,
    DistributorAssignmentItemOut,
)
from app.schemas.common import Page, paginated
from app.services import assignment_service

DbDep = Annotated[Session, Depends(get_db)]
router = APIRouter(tags=["assignments"])


@router.get("/distributors/me/assignments", response_model=list[DistributorAssignmentItemOut])
def my_assignments(user: CurrentUserDep, db: DbDep):
    return [
        DistributorAssignmentItemOut.model_validate(item)
        for item in assignment_service.distributor_me_assignments(db, user=user.user)
    ]


@router.get("/assignments", response_model=Page[AssignmentOut])
def list_assignments(
    user: CurrentUserDep,
    db: DbDep,
    pagination: PaginationDep,
    campaign_id: uuid.UUID | None = Query(default=None),
):
    rows, total = assignment_service.list_assignments(
        db, user=user.user, campaign_id=campaign_id, limit=pagination.limit, offset=pagination.offset
    )
    return paginated(
        [AssignmentOut.model_validate(a) for a in rows], total, pagination.limit, pagination.offset
    )


@router.get("/assignments/{assignment_id}", response_model=AssignmentOut)
def get_assignment(assignment_id: uuid.UUID, user: CurrentUserDep, db: DbDep):
    return AssignmentOut.model_validate(
        assignment_service.get_assignment_scoped(db, user=user.user, assignment_id=assignment_id)
    )


@router.post("/assignments", response_model=AssignmentOut, status_code=201)
def create_assignment(payload: AssignmentIn, admin: AdminDep, db: DbDep, ctx: RequestCtx):
    assignment = assignment_service.create_assignment(
        db, admin=admin.user, data=payload.model_dump(exclude_unset=True), ctx=ctx
    )
    db.commit()
    return AssignmentOut.model_validate(assignment)


@router.patch("/assignments/{assignment_id}", response_model=AssignmentOut)
def update_assignment(
    assignment_id: uuid.UUID, payload: AssignmentPatchIn, admin: AdminDep, db: DbDep, ctx: RequestCtx
):
    assignment = assignment_service.update_assignment(
        db,
        admin=admin.user,
        assignment_id=assignment_id,
        data=payload.model_dump(exclude_unset=True),
        ctx=ctx,
    )
    db.commit()
    return AssignmentOut.model_validate(assignment)
