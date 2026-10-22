"""Password, token and opaque-key helpers."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

MIN_PASSWORD_LENGTH = 10


def hash_password(password: str) -> str:
    return make_password(password)


def verify_password(password_hash: str, password: str) -> bool:
    if not password_hash:
        return False
    try:
        return check_password(password, password_hash)
    except Exception:  # noqa: BLE001 - malformed hash must not crash login
        return False


def validate_password_strength(password: str) -> list[str]:
    problems: list[str] = []
    if len(password) < MIN_PASSWORD_LENGTH:
        problems.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if not any(c.isdigit() for c in password):
        problems.append("Password must contain at least one digit.")
    if not any(c.isalpha() for c in password):
        problems.append("Password must contain at least one letter.")
    return problems


def _digest(value: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()


def hash_token(raw: str) -> str:
    return _digest(raw)


# Compatibility name used by the old service layer.
hash_refresh_token = hash_token


def digest_bytes_sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def opaque_object_key(prefix: str) -> str:
    return f"{prefix}/{uuid.uuid4().hex}/{secrets.token_hex(8)}"


def new_raw_token() -> str:
    return secrets.token_urlsafe(48)


def new_invitation_token() -> tuple[str, str, datetime]:
    raw = new_raw_token()
    expires = timezone.now() + timedelta(hours=72)
    return raw, hash_token(raw), expires


def new_password_reset_token() -> tuple[str, str, datetime]:
    raw = new_raw_token()
    expires = timezone.now() + timedelta(hours=1)
    return raw, hash_token(raw), expires
