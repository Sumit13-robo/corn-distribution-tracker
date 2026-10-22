"""Auth routes: login, refresh (cookie), logout, me, invitations, resets."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.api.dependencies import AdminDep, CurrentUserDep, RequestCtx, client_ip_key
from app.core.config import get_settings
from app.core.errors import AuthRequiredError
from app.core.security import create_access_token
from app.db.session import get_db as db_dep
from app.models import Invitation
from app.schemas.auth import (
    AcceptInvitationIn,
    AckOut,
    ChangePasswordIn,
    ForgotPasswordIn,
    InvitationCreatedOut,
    InvitationCreateIn,
    InvitationOut,
    LoginIn,
    LoginOut,
    RefreshOut,
    ResetPasswordIn,
    UserOut,
)
from app.services import auth_service

DbDep = Annotated[OrmSession, Depends(db_dep)]

router = APIRouter(tags=["auth"])


def _user_out(user) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email_normalized,
        display_name=user.display_name,
        role=user.role.value,
        is_active=user.is_active,
        must_reset_password=user.must_reset_password,
        last_login_at=user.last_login_at,
    )


def _access_payload(user) -> LoginOut:
    token, expires_at = create_access_token(user.id, user.role.value)
    ttl = int(expires_at.timestamp() - datetime.now(UTC).timestamp())
    return LoginOut(access_token=token, expires_in=max(ttl, 0), user=_user_out(user))


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    settings = get_settings()
    samesite_map: dict[str, Literal["lax", "strict", "none"]] = {
        "Lax": "lax",
        "Strict": "strict",
        "None": "none",
    }
    samesite: Literal["lax", "strict", "none"] = samesite_map[settings.cookie_samesite]
    response.set_cookie(
        key="refresh_token",
        value=raw_token,
        max_age=int(timedelta(days=settings.refresh_token_ttl_days).total_seconds()),
        secure=settings.cookie_secure,
        httponly=True,
        samesite=samesite,
        domain=settings.cookie_domain or None,
        path="/api/v1/auth",
    )


@router.post("/auth/login", response_model=LoginOut)
def login(payload: LoginIn, request: Request, response: Response, db: DbDep, ctx: RequestCtx):
    user, raw_token, _row = auth_service.authenticate_login(
        db,
        email=payload.email,
        password=payload.password,
        ctx=ctx,
        ip_key=client_ip_key(request, payload.email),
    )
    db.commit()
    body = _access_payload(user)
    _set_refresh_cookie(response, raw_token)
    return body


@router.post("/auth/refresh", response_model=RefreshOut)
def refresh(request: Request, response: Response, db: DbDep, ctx: RequestCtx):
    raw = request.cookies.get("refresh_token")
    if not raw:
        raise AuthRequiredError("No refresh session found.")
    user, new_raw, _row = auth_service.rotate_refresh(db, raw, ctx)
    db.commit()
    body = _access_payload(user)
    _set_refresh_cookie(response, new_raw)
    return body


@router.post("/auth/logout", response_model=AckOut)
def logout(request: Request, response: Response, db: DbDep, ctx: RequestCtx):
    raw = request.cookies.get("refresh_token")
    if raw:
        auth_service.revoke_refresh_family(db, raw, ctx)
        db.commit()
    response.delete_cookie("refresh_token", path="/api/v1/auth")
    return AckOut(message="Signed out.")


@router.get("/auth/me", response_model=UserOut)
def me(user: CurrentUserDep):
    return _user_out(user.user)


@router.post("/auth/change-password", response_model=AckOut)
def change_password(payload: ChangePasswordIn, user: CurrentUserDep, db: DbDep, ctx: RequestCtx):
    auth_service.change_password(
        db,
        user=user.user,
        current_password=payload.current_password,
        new_password=payload.new_password,
        ctx=ctx,
    )
    db.commit()
    return AckOut(message="Password updated.")


@router.post("/auth/forgot-password", response_model=AckOut)
def forgot_password(payload: ForgotPasswordIn, request: Request, db: DbDep, ctx: RequestCtx):
    auth_service.request_password_reset(
        db, email=payload.email, ctx=ctx, ip_key=client_ip_key(request, payload.email)
    )
    db.commit()
    # Generic response: does not reveal whether the account exists.
    return AckOut(
        message="If that account exists, reset instructions have been issued through the configured channel."
    )


@router.post("/auth/reset-password", response_model=AckOut)
def reset_password(payload: ResetPasswordIn, db: DbDep, ctx: RequestCtx):
    auth_service.reset_password(db, raw_token=payload.token, password=payload.password, ctx=ctx)
    db.commit()
    return AckOut(message="Password updated; all previous sessions were revoked.")


@router.post("/auth/accept-invitation", response_model=UserOut)
def accept_invitation(payload: AcceptInvitationIn, request: Request, db: DbDep, ctx: RequestCtx):
    user = auth_service.accept_invitation(
        db, raw_token=payload.token, password=payload.password, display_name=payload.display_name, ctx=ctx
    )
    db.commit()
    return _user_out(user)


@router.post("/admin/users/invitations", response_model=InvitationCreatedOut, status_code=201)
def create_invitation(payload: InvitationCreateIn, admin: AdminDep, db: DbDep, ctx: RequestCtx):
    invite, raw_token = auth_service.create_invitation(
        db,
        admin=admin.user,
        email=payload.email,
        display_name=payload.display_name,
        role=payload.role,
        ctx=ctx,
    )
    db.commit()
    return InvitationCreatedOut(
        id=invite.id,
        email=invite.email_normalized,
        display_name=invite.display_name,
        role=invite.role.value,
        expires_at=invite.expires_at,
        accepted_at=invite.accepted_at,
        revoked_at=invite.revoked_at,
        created_at=invite.created_at,
        invite_token=raw_token,
    )


@router.get("/admin/users/invitations", response_model=list[InvitationOut])
def list_invitations(admin: AdminDep, db: DbDep):
    invites = list(db.scalars(select(Invitation).order_by(Invitation.created_at.desc()).limit(100)))
    return [
        InvitationOut(
            id=invite.id,
            email=invite.email_normalized,
            display_name=invite.display_name,
            role=invite.role.value,
            expires_at=invite.expires_at,
            accepted_at=invite.accepted_at,
            revoked_at=invite.revoked_at,
            created_at=invite.created_at,
        )
        for invite in invites
    ]
