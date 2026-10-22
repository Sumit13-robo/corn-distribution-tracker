"""Auth request/response schemas per docs/architecture/API_CONTRACT.md."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field

from app.schemas.common import ApiModel

RoleLiteral = Literal["ADMIN", "DISTRIBUTOR"]


class UserOut(ApiModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: RoleLiteral
    is_active: bool
    must_reset_password: bool
    last_login_at: datetime | None = None


class LoginIn(ApiModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class LoginOut(ApiModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - fixed non-secret schema literal
    expires_in: int
    user: UserOut


class RefreshOut(ApiModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - fixed non-secret schema literal
    expires_in: int
    user: UserOut


class ForgotPasswordIn(ApiModel):
    email: EmailStr


class AckOut(ApiModel):
    status: Literal["ok"] = "ok"
    message: str


class ResetPasswordIn(ApiModel):
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class ChangePasswordIn(ApiModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=1, max_length=200)


class AcceptInvitationIn(ApiModel):
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=1, max_length=200)
    display_name: str | None = Field(default=None, max_length=120)


class InvitationCreateIn(ApiModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)
    role: RoleLiteral = "DISTRIBUTOR"


class InvitationOut(ApiModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: RoleLiteral
    expires_at: datetime
    accepted_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime


class InvitationCreatedOut(InvitationOut):
    """Raw token returned exactly once; never logged or stored in plaintext."""

    invite_token: str
