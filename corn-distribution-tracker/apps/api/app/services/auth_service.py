"""Authentication domain service: login, refresh rotation, invitations, resets.

Security properties (docs/architecture/SECURITY_AND_PRIVACY.md):
- Argon2id password hashing; generic failure messages (no account enumeration).
- Refresh tokens stored as HMAC digests only, rotated on use, with family reuse
  detection revoking the whole family.
- Login lockout after repeated failures plus per-request rate limiting upstream.
- Every sensitive action writes an audit event.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, AuthRequiredError, ConflictError
from app.core.rate_limit import hit
from app.core.security import (
    hash_password,
    hash_refresh_token,
    needs_password_rehash,
    new_invitation_token,
    new_password_reset_token,
    new_refresh_token,
    validate_password_strength,
    verify_password,
)
from app.models import Invitation, PasswordResetToken, RefreshToken, Role, User
from app.services import settings_service
from app.services.audit_service import RequestContext, record_audit

MAX_FAILED_LOGINS = 10
LOCKOUT_MINUTES = 15


def _norm_email(email: str) -> str:
    return email.strip().lower()


def normalize_email(email: str) -> str:
    return _norm_email(email)


_EMAIL_ADAPTER = TypeAdapter(EmailStr)


def _validated_email(email: str) -> str:
    """Validate with the same rules as the API boundary (rejects reserved TLDs)."""
    try:
        validated = _EMAIL_ADAPTER.validate_python(email)
    except ValidationError:
        raise AppError("A valid email address is required.", details=[{"field": "email"}]) from None
    return _norm_email(str(validated))


def ensure_core_org_rows(db: Session, *, created_by: uuid.UUID | None = None) -> tuple[User | None, Any]:
    """Ensure org settings and the single central account exist (bootstrap helper)."""
    from app.models import AccountType, StockAccount

    settings_service.get_or_create_settings(db)
    central = db.scalar(select(StockAccount).where(StockAccount.account_type == AccountType.CENTRAL))
    if central is None:
        central = StockAccount(account_type=AccountType.CENTRAL, name="Central warehouse", is_active=True)
        db.add(central)
        db.flush()
    return None, central


def authenticate_login(
    db: Session, *, email: str, password: str, ctx: RequestContext, ip_key: str
) -> tuple[User, str, RefreshToken]:
    allowed, retry_after = hit("auth.login", ip_key)
    if not allowed:
        raise AppError(
            "Too many attempts; try again later.",
            code="RATE_LIMITED",
            status_code=429,
            details=[{"retry_after": retry_after}],
        )

    normalized = _norm_email(email)
    user = db.scalar(select(User).where(User.email_normalized == normalized))
    generic = AppError("Invalid email or password.", code="UNAUTHENTICATED", status_code=401)
    if user is None:
        # equal-cost failure path
        verify_password(hash_password("timing-equalizer-not-a-real-hash"), password)
        raise generic
    if user.locked_until and user.locked_until > datetime.now(UTC):
        raise AppError(
            "Account temporarily locked after repeated failures; try again later.",
            code="RATE_LIMITED",
            status_code=429,
        )
    if not user.password_hash or not verify_password(user.password_hash, password):
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= MAX_FAILED_LOGINS:
            user.locked_until = datetime.now(UTC) + timedelta(minutes=LOCKOUT_MINUTES)
            user.failed_login_count = 0
        record_audit(
            db, actor=user, action="auth.login_failed", target_type="user", target_id=user.id, ctx=ctx
        )
        # Failure counters, lockout and audit must persist despite the raised error.
        db.commit()
        raise generic
    if not user.is_active:
        record_audit(
            db, actor=user, action="auth.login_inactive", target_type="user", target_id=user.id, ctx=ctx
        )
        db.commit()
        raise generic
    if needs_password_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = datetime.now(UTC)
    raw, token_row = issue_refresh_family(db, user)
    record_audit(db, actor=user, action="auth.login", target_type="user", target_id=user.id, ctx=ctx)
    db.flush()
    return user, raw, token_row


def issue_refresh_family(db: Session, user: User) -> tuple[str, RefreshToken]:
    settings = get_settings()
    raw, digest = new_refresh_token()
    row = RefreshToken(
        user_id=user.id,
        family_id=uuid.uuid4(),
        token_hash=digest,
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days),
    )
    db.add(row)
    db.flush()
    return raw, row


def rotate_refresh(db: Session, raw_token: str, ctx: RequestContext) -> tuple[User, str, RefreshToken]:
    digest = hash_refresh_token(raw_token)
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == digest))
    if row is None:
        raise AuthRequiredError("Invalid session.")
    if row.revoked_at is not None:
        # Reuse detection: revoke the entire family and force re-login. The
        # request session rolls back on a raised exception, so persist the
        # revocation + audit explicitly: security state must survive the 401.
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == row.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC), revoked_reason="reused")
        )
        record_audit(
            db,
            actor=None,
            action="auth.refresh_reuse_detected",
            target_type="refresh_token",
            target_id=row.id,
            ctx=ctx,
        )
        db.commit()
        raise AuthRequiredError("Session expired; sign in again.")
    if row.expires_at < datetime.now(UTC):
        raise AuthRequiredError("Session expired; sign in again.")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise AuthRequiredError("Session expired; sign in again.")
    row.revoked_at = datetime.now(UTC)
    row.revoked_reason = "rotated"
    raw, new_row = issue_refresh_family(db, user)
    new_row.family_id = row.family_id
    new_row.last_used_at = datetime.now(UTC)
    db.flush()
    return user, raw, new_row


def revoke_refresh_family(
    db: Session, raw_token: str, ctx: RequestContext, reason: str = "revoked_on_logout"
) -> None:
    digest = hash_refresh_token(raw_token)
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == digest))
    if row is None:
        return
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == row.family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC), revoked_reason=reason)
    )
    record_audit(
        db, actor=row.user_id, action=f"auth.{reason}", target_type="user", target_id=row.user_id, ctx=ctx
    )
    db.flush()


def create_invitation(
    db: Session,
    *,
    admin: User,
    email: str,
    display_name: str,
    role: str,
    ctx: RequestContext,
) -> tuple[Invitation, str]:
    normalized = _norm_email(email)
    existing_user = db.scalar(select(User).where(User.email_normalized == normalized))
    open_invite = db.scalar(
        select(Invitation).where(
            Invitation.email_normalized == normalized,
            Invitation.accepted_at.is_(None),
            Invitation.revoked_at.is_(None),
            Invitation.expires_at > datetime.now(UTC),
        )
    )
    if existing_user is not None or open_invite is not None:
        raise ConflictError("A user with this email already exists or is already invited.")
    try:
        role_enum = Role(str(role))
    except ValueError:
        raise AppError("Role must be ADMIN or DISTRIBUTOR.", details=[{"field": "role"}]) from None
    raw, digest, expires = new_invitation_token()
    invite = Invitation(
        email_normalized=normalized,
        display_name=display_name,
        role=role_enum,
        token_hash=digest,
        created_by=admin.id,
        expires_at=expires,
    )
    db.add(invite)
    record_audit(
        db,
        actor=admin,
        action="invitation.created",
        target_type="invitation",
        target_id=invite.id,
        details={"email_domain": normalized.split("@")[-1], "role": role_enum.value},
        ctx=ctx,
    )
    db.flush()
    return invite, raw


def accept_invitation(
    db: Session, *, raw_token: str, password: str, display_name: str | None, ctx: RequestContext
) -> User:
    allowed, retry_after = hit("auth.invite_accept", ctx.ip or "unknown")
    if not allowed:
        raise AppError(
            "Too many attempts; try again later.",
            code="RATE_LIMITED",
            status_code=429,
            details=[{"retry_after": retry_after}],
        )
    problems = validate_password_strength(password)
    if problems:
        raise AppError(problems[0], details=[{"field": "password"}])
    digest = hash_refresh_token(raw_token)
    invite = db.scalar(select(Invitation).where(Invitation.token_hash == digest))
    if (
        invite is None
        or invite.accepted_at is not None
        or invite.revoked_at is not None
        or invite.expires_at < datetime.now(UTC)
    ):
        raise AppError(
            "This invitation link is invalid or has expired.", status_code=400, code="VALIDATION_ERROR"
        )
    user: User | None = None
    if invite.user_id:
        user = db.get(User, invite.user_id)
    if user is None:
        user = db.scalar(select(User).where(User.email_normalized == invite.email_normalized))
    if user is None:
        user = User(
            email_normalized=invite.email_normalized, display_name=invite.display_name, role=invite.role
        )
        db.add(user)
    user.display_name = display_name or user.display_name
    user.role = invite.role
    user.is_active = True
    user.password_hash = hash_password(password)
    user.must_reset_password = False
    invite.accepted_at = datetime.now(UTC)
    invite.user_id = user.id
    record_audit(
        db, actor=user, action="auth.invitation_accepted", target_type="user", target_id=user.id, ctx=ctx
    )
    db.flush()
    return user


def request_password_reset(db: Session, *, email: str, ctx: RequestContext, ip_key: str) -> None:
    allowed, _ = hit("auth.password_reset", ip_key)
    if not allowed:
        return  # silently ignore over-limit requests; response stays generic
    normalized = _norm_email(email)
    user = db.scalar(select(User).where(User.email_normalized == normalized, User.is_active.is_(True)))
    if user is None:
        return  # generic response; do not reveal existence
    raw, digest, expires = new_password_reset_token()
    db.add(PasswordResetToken(user_id=user.id, token_hash=digest, expires_at=expires))
    record_audit(
        db, actor=user, action="auth.password_reset_requested", target_type="user", target_id=user.id, ctx=ctx
    )
    db.flush()
    # Delivery channel is the operator's secure channel in the first release; the raw
    # token is never logged or returned. Reset completion flows through /auth/reset-password.
    # Test-only back channel on the instance, intentionally untyped/excluded from serialization.
    setattr(user, "_pending_reset_token_for_tests", raw)  # noqa: B010


def reset_password(db: Session, *, raw_token: str, password: str, ctx: RequestContext) -> None:
    digest = hash_refresh_token(raw_token)
    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == digest))
    if row is None or row.used_at is not None or row.expires_at < datetime.now(UTC):
        raise AppError("This reset link is invalid or has expired.", status_code=400, code="VALIDATION_ERROR")
    problems = validate_password_strength(password)
    if problems:
        raise AppError(problems[0], details=[{"field": "password"}])
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise AppError("This reset link is invalid or has expired.", status_code=400, code="VALIDATION_ERROR")
    user.password_hash = hash_password(password)
    user.must_reset_password = False
    row.used_at = datetime.now(UTC)
    # Revoke all sessions of the user.
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC), revoked_reason="password_reset")
    )
    record_audit(
        db, actor=user, action="auth.password_reset_completed", target_type="user", target_id=user.id, ctx=ctx
    )
    db.flush()


def change_password(
    db: Session, *, user: User, current_password: str, new_password: str, ctx: RequestContext
) -> None:
    if not user.password_hash or not verify_password(user.password_hash, current_password):
        raise AppError("Current password is incorrect.", details=[{"field": "current_password"}])
    problems = validate_password_strength(new_password)
    if problems:
        raise AppError(problems[0], details=[{"field": "new_password"}])
    user.password_hash = hash_password(new_password)
    user.must_reset_password = False
    record_audit(
        db, actor=user, action="auth.password_changed", target_type="user", target_id=user.id, ctx=ctx
    )
    db.flush()


def deactivate_user(db: Session, *, admin: User, target: User, ctx: RequestContext) -> None:
    if target.id == admin.id:
        raise AppError("You cannot deactivate your own account.")
    if target.role == "ADMIN" and not _other_active_admin_exists(db, exclude_user_id=target.id):
        raise AppError("The last active administrator cannot be deactivated.")
    target.is_active = False
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == target.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC), revoked_reason="user_deactivated")
    )
    record_audit(db, actor=admin, action="user.deactivated", target_type="user", target_id=target.id, ctx=ctx)
    db.flush()


def _other_active_admin_exists(db: Session, *, exclude_user_id: uuid.UUID) -> bool:
    return (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == "ADMIN", User.is_active.is_(True), User.id != exclude_user_id)
        )
        or 0
    ) > 1


def create_first_admin(
    db: Session, *, email: str, password: str, display_name: str | None, ctx: RequestContext | None = None
) -> User:
    """One-time controlled bootstrap; refuses duplicate admins (no public elevation)."""
    normalized_email = _validated_email(email)
    existing_admin = db.scalar(select(func.count()).select_from(User).where(User.role == "ADMIN"))
    if existing_admin:
        raise ConflictError("An administrator already exists; use invitations for additional accounts.")
    problems = validate_password_strength(password)
    if problems:
        raise AppError(problems[0])
    user = User(
        email_normalized=normalized_email,
        display_name=display_name or "Administrator",
        role="ADMIN",
        is_active=True,
        password_hash=hash_password(password),
    )
    db.add(user)
    ensure_core_org_rows(db)
    record_audit(
        db, actor=user, action="auth.admin_bootstrapped", target_type="user", target_id=user.id, ctx=ctx
    )
    db.flush()
    return user
