"""Security primitives: password hashing, access tokens, refresh token handling.

- Passwords: Argon2id with reviewed parameters (see docs/architecture/SECURITY_AND_PRIVACY.md).
- Access tokens: short-lived signed JWTs (HS256) carrying the minimum identity claims;
  role/ownership is always re-derived from the database on each request.
- Refresh tokens: random URL-safe strings; only their SHA-256 digest is ever stored,
  with rotation and family-level reuse detection.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings

password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=64 * 1024,  # 64 MiB
    parallelism=2,
)

Role = Literal["ADMIN", "DISTRIBUTOR"]


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_password_rehash(password_hash: str) -> bool:
    try:
        return password_hasher.check_needs_rehash(password_hash)
    except Exception:  # noqa: BLE001 - malformed hashes must not crash login paths
        return False


MIN_PASSWORD_LENGTH = 10


def validate_password_strength(password: str) -> list[str]:
    problems: list[str] = []
    if len(password) < MIN_PASSWORD_LENGTH:
        problems.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if not any(c.isdigit() for c in password):
        problems.append("Password must contain at least one digit.")
    if not any(c.isalpha() for c in password):
        problems.append("Password must contain at least one letter.")
    return problems


def create_access_token(user_id: uuid.UUID, role: str) -> tuple[str, datetime]:
    settings = get_settings()
    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=settings.access_token_ttl_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "iat": int(issued_at.timestamp()),
        "nbf": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "typ": "access",
        "jti": secrets.token_hex(8),
    }
    token = jwt_encode(payload)
    return token, expires_at


def jwt_encode(payload: dict[str, Any]) -> str:
    import jwt as _jwt

    return _jwt.encode(payload, get_settings().secret_key, algorithm="HS256")


def jwt_decode(token: str) -> dict[str, Any]:
    import jwt as _jwt

    return _jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])


def new_refresh_token() -> tuple[str, str]:
    """Return (raw_token, sha256_digest). The raw token is shown once to the client;
    only the digest is persisted."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    return hashlib_sha256(raw)


def hashlib_sha256(value: str) -> str:
    digest = hmac.new(get_settings().secret_key.encode(), value.encode(), "sha256").hexdigest()
    return digest


def digest_bytes_sha256_hex(data: bytes) -> str:

    return hashlib.sha256(data).hexdigest()


def opaque_object_key(prefix: str) -> str:
    """Private storage keys must be opaque: no user/site/personal information."""
    return f"{prefix}/{uuid.uuid4().hex}/{secrets.token_hex(8)}"


def new_invitation_token() -> tuple[str, str, datetime]:
    raw, digest = new_refresh_token()
    expires = datetime.now(UTC) + timedelta(hours=72)
    return raw, digest, expires


def new_password_reset_token() -> tuple[str, str, datetime]:
    raw, digest = new_refresh_token()
    expires = datetime.now(UTC) + timedelta(hours=1)
    return raw, digest, expires
