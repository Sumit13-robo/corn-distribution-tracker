"""Authentication, invitations, resets and account lifecycle.

Django sessions replace the former access/refresh-token pair. The browser holds
only an HttpOnly session cookie; CSRF protection is enforced by DRF for unsafe
authenticated requests. Password hashing is Argon2id (Django hasher).
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

from django.contrib.auth.hashers import make_password
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.utils import timezone

from ..enums import Role
from ..errors import AppError, AuthRequiredError, ConflictError, RateLimitedError
from ..models import Invitation, PasswordResetToken, User
from ..rate_limit import hit
from ..security import (
    hash_token,
    new_invitation_token,
    new_password_reset_token,
    validate_password_strength,
    verify_password,
)
from . import settings as settings_service_
from .audit import RequestContext, record_audit
from .inventory import ensure_core_org_rows

MAX_FAILED_LOGINS = 10
LOCKOUT_MINUTES = 15
DUMMY_PASSWORD_HASH = make_password("timing-equalizer-not-a-real-password")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _validated_email(email: str) -> str:
    normalized = normalize_email(email)
    try:
        validate_email(normalized)
    except DjangoValidationError:
        raise AppError("A valid email address is required.", details=[{"field": "email"}]) from None
    return normalized


def authenticate_login(*, email: str, password: str, ctx: RequestContext, ip_key: str) -> User:
    allowed, retry_after = hit("auth.login", ip_key)
    if not allowed:
        raise RateLimitedError(retry_after=retry_after)

    normalized = normalize_email(email)
    user = User.objects.filter(email=normalized).first()
    generic = AuthRequiredError("Invalid email or password.")
    if user is None:
        verify_password(DUMMY_PASSWORD_HASH, password)
        raise generic
    if user.locked_until and user.locked_until > timezone.now():
        raise RateLimitedError(
            "Account temporarily locked after repeated failures; try again later."
        )
    if not user.password or not verify_password(user.password, password):
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= MAX_FAILED_LOGINS:
            user.locked_until = timezone.now() + timedelta(minutes=LOCKOUT_MINUTES)
            user.failed_login_count = 0
        user.save(update_fields=["failed_login_count", "locked_until", "updated_at"])
        record_audit(
            actor=user,
            action="auth.login_failed",
            target_type="user",
            target_id=user.id,
            ctx=ctx,
        )
        raise generic
    if not user.is_active:
        record_audit(
            actor=user,
            action="auth.login_inactive",
            target_type="user",
            target_id=user.id,
            ctx=ctx,
        )
        raise generic

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login = timezone.now()
    user.save(update_fields=["failed_login_count", "locked_until", "last_login", "updated_at"])
    record_audit(actor=user, action="auth.login", target_type="user", target_id=user.id, ctx=ctx)
    return user


def logout_audit(*, user: User, ctx: RequestContext) -> None:
    record_audit(
        actor=user,
        action="auth.logout",
        target_type="user",
        target_id=user.id,
        ctx=ctx,
    )


def create_invitation(
    *,
    admin: User,
    email: str,
    display_name: str,
    role: str,
    ctx: RequestContext,
) -> tuple[Invitation, str]:
    normalized = normalize_email(email)
    try:
        validate_email(normalized)
    except DjangoValidationError:
        raise AppError("A valid email address is required.", details=[{"field": "email"}]) from None
    existing_user = User.objects.filter(email=normalized).first()
    open_invite = Invitation.objects.filter(
        email=normalized,
        accepted_at__isnull=True,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).first()
    if existing_user is not None or open_invite is not None:
        raise ConflictError("A user with this email already exists or is already invited.")
    try:
        role_value = Role(role)
    except ValueError:
        raise AppError("Role must be ADMIN or DISTRIBUTOR.", details=[{"field": "role"}]) from None
    raw, digest, expires = new_invitation_token()
    invite = Invitation.objects.create(
        email=normalized,
        display_name=display_name,
        role=role_value,
        token_hash=digest,
        created_by=admin,
        expires_at=expires,
    )
    record_audit(
        actor=admin,
        action="invitation.created",
        target_type="invitation",
        target_id=invite.id,
        details={"email_domain": normalized.split("@")[-1], "role": role_value},
        ctx=ctx,
    )
    return invite, raw


def accept_invitation(
    *, raw_token: str, password: str, display_name: str | None, ctx: RequestContext
) -> User:
    allowed, retry_after = hit("auth.invite_accept", ctx.ip or "unknown")
    if not allowed:
        raise RateLimitedError(retry_after=retry_after)
    problems = validate_password_strength(password)
    if problems:
        raise AppError(problems[0], details=[{"field": "password"}])
    invite = Invitation.objects.filter(token_hash=hash_token(raw_token)).first()
    if (
        invite is None
        or invite.accepted_at is not None
        or invite.revoked_at is not None
        or invite.expires_at < timezone.now()
    ):
        raise AppError(
            "This invitation link is invalid or has expired.",
            status_code=400,
            code="VALIDATION_ERROR",
        )
    user = User.objects.filter(id=invite.user_id).first() if invite.user_id else None
    if user is None:
        user = User.objects.filter(email=invite.email).first()
    if user is None:
        user = User(email=invite.email, display_name=invite.display_name, role=invite.role)
    user.display_name = display_name or user.display_name
    user.role = invite.role
    user.is_active = True
    user.set_password(password)
    user.must_reset_password = False
    user.save()
    invite.accepted_at = timezone.now()
    invite.user = user
    invite.save(update_fields=["accepted_at", "user", "updated_at"])
    record_audit(
        actor=user,
        action="auth.invitation_accepted",
        target_type="user",
        target_id=user.id,
        ctx=ctx,
    )
    return user


def request_password_reset(*, email: str, ctx: RequestContext, ip_key: str) -> str | None:
    allowed, _ = hit("auth.password_reset", ip_key)
    if not allowed:
        return None
    return issue_password_reset(email=email, ctx=ctx)


def issue_password_reset(*, email: str, ctx: RequestContext | None = None) -> str | None:
    """Create a one-time reset token and return the raw value to the operator.

    The HTTP endpoint discards the return value so it can answer generically.
    Operators deliver it through the configured secure channel (for example the
    `issue_password_reset` management command). Raw tokens are never stored or
    logged.
    """
    normalized = normalize_email(email)
    user = User.objects.filter(email=normalized, is_active=True).first()
    if user is None:
        return None
    raw, digest, expires = new_password_reset_token()
    PasswordResetToken.objects.create(user=user, token_hash=digest, expires_at=expires)
    record_audit(
        actor=user,
        action="auth.password_reset_requested",
        target_type="user",
        target_id=user.id,
        ctx=ctx,
    )
    # The delivery channel is the operator's secure channel. This transient
    # attribute is used only by tests and is never serialized or logged.
    user._pending_reset_token_for_tests = raw  # type: ignore[attr-defined]
    return raw


def reset_password(*, raw_token: str, password: str, ctx: RequestContext) -> User:
    row = PasswordResetToken.objects.filter(token_hash=hash_token(raw_token)).first()
    if row is None or row.used_at is not None or row.expires_at < timezone.now():
        raise AppError(
            "This reset link is invalid or has expired.", status_code=400, code="VALIDATION_ERROR"
        )
    problems = validate_password_strength(password)
    if problems:
        raise AppError(problems[0], details=[{"field": "password"}])
    user = User.objects.filter(id=row.user_id, is_active=True).first()
    if user is None:
        raise AppError(
            "This reset link is invalid or has expired.", status_code=400, code="VALIDATION_ERROR"
        )
    user.set_password(password)
    user.must_reset_password = False
    user.save()
    row.used_at = timezone.now()
    row.save(update_fields=["used_at", "updated_at"])
    flush_user_sessions(user.id)
    record_audit(
        actor=user,
        action="auth.password_reset_completed",
        target_type="user",
        target_id=user.id,
        ctx=ctx,
    )
    return user


def change_password(
    *, user: User, current_password: str, new_password: str, ctx: RequestContext
) -> User:
    if not verify_password(user.password, current_password):
        raise AppError(
            "Current password is incorrect.", details=[{"field": "current_password"}]
        )
    problems = validate_password_strength(new_password)
    if problems:
        raise AppError(problems[0], details=[{"field": "new_password"}])
    user.set_password(new_password)
    user.must_reset_password = False
    user.save()
    record_audit(
        actor=user,
        action="auth.password_changed",
        target_type="user",
        target_id=user.id,
        ctx=ctx,
    )
    return user


def deactivate_user(*, admin: User, target: User, ctx: RequestContext) -> None:
    if target.id == admin.id:
        raise AppError("You cannot deactivate your own account.")
    if target.role == Role.ADMIN:
        other_admins = User.objects.filter(role=Role.ADMIN, is_active=True).exclude(id=target.id)
        if not other_admins.exists():
            raise AppError("The last active administrator cannot be deactivated.")
    target.is_active = False
    target.save(update_fields=["is_active", "updated_at"])
    flush_user_sessions(target.id)
    record_audit(
        actor=admin,
        action="user.deactivated",
        target_type="user",
        target_id=target.id,
        ctx=ctx,
    )


def create_first_admin(
    *, email: str, password: str, display_name: str | None, ctx: RequestContext | None = None
) -> User:
    normalized_email = _validated_email(email)
    if User.objects.filter(role=Role.ADMIN).exists():
        raise ConflictError("An administrator already exists; use invitations for additional accounts.")
    problems = validate_password_strength(password)
    if problems:
        raise AppError(problems[0])
    user = User(
        email=normalized_email,
        display_name=display_name or "Administrator",
        role=Role.ADMIN,
        is_active=True,
    )
    user.set_password(password)
    user.save()
    ensure_core_org_rows(created_by=user.id)
    settings_service_.get_or_create_settings()
    record_audit(
        actor=user,
        action="auth.admin_bootstrapped",
        target_type="user",
        target_id=user.id,
        ctx=ctx,
    )
    return user


def flush_user_sessions(user_id: uuid.UUID) -> None:
    """Remove all database-backed sessions belonging to a user.

    Django's session backend doesn't expose a user index, so this small app
    decodes sessions. It is used on password reset/deactivation to revoke every
    outstanding browser session immediately.
    """
    target = str(user_id)
    for session in Session.objects.filter(expire_date__gte=timezone.now()).iterator():
        try:
            data: dict[str, Any] = session.get_decoded()
        except Exception:  # noqa: BLE001, S112 - corrupt sessions are ignored and can expire
            continue
        if data.get("_auth_user_id") == target:
            session.delete()
