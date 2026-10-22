"""API dependencies: identity, RBAC, request context, pagination, org settings.

Server authorization is authoritative: role and ownership are always derived from the
authenticated session + database, never from client-supplied fields.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

import jwt as pyjwt
from fastapi import Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AuthRequiredError, ForbiddenError
from app.core.security import jwt_decode
from app.db.session import get_db
from app.models import OrganizationSettings, User
from app.services import settings_service
from app.services.audit_service import RequestContext


@dataclass
class CurrentUser:
    user: User

    @property
    def id(self) -> uuid.UUID:
        return self.user.id

    @property
    def is_admin(self) -> bool:
        return self.user.role == "ADMIN"


def _extract_bearer(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer ") and len(header) > 7:
        return header[7:]
    return None


def get_current_user(request: Request, db: Annotated[Session, Depends(get_db)]) -> CurrentUser:
    token = _extract_bearer(request)
    if not token:
        raise AuthRequiredError("Authentication required.")
    try:
        payload = jwt_decode(token)
    except pyjwt.ExpiredSignatureError:
        raise AuthRequiredError("Session expired; refresh required.") from None
    except pyjwt.InvalidTokenError:
        raise AuthRequiredError("Invalid session token.") from None
    user_id = payload.get("sub")
    if not user_id:
        raise AuthRequiredError("Invalid session token.")
    user = db.get(User, uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise AuthRequiredError("Session no longer valid.")
    return CurrentUser(user=user)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_admin(user: CurrentUserDep) -> CurrentUser:
    if not user.is_admin:
        raise ForbiddenError("Administrator role required.")
    return user


AdminDep = Annotated[CurrentUser, Depends(require_admin)]


def get_request_context(request: Request) -> RequestContext:
    return RequestContext(
        request_id=getattr(request.state, "request_id", None),
        ip=(request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
    )


RequestCtx = Annotated[RequestContext, Depends(get_request_context)]


def get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def get_org_settings(db: Annotated[Session, Depends(get_db)]) -> OrganizationSettings:
    return settings_service.get_or_create_settings(db)


OrgSettingsDep = Annotated[OrganizationSettings, Depends(get_org_settings)]


class Pagination:
    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=100)] = 25,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> None:
        self.limit = limit
        self.offset = offset


PaginationDep = Annotated[Pagination, Depends(Pagination)]


def client_ip_key(request: Request, email: str | None = None) -> str:
    """Rate limit key: prefer client IP plus (when present) the attempted email."""
    ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and get_settings().cookie_secure:
        ip = forwarded.split(",")[0].strip()
    return f"{ip}:{email or '-'}"
