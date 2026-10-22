"""Audit event schemas (read-only)."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.schemas.common import ApiModel


class AuditEventOut(ApiModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None = None
    action: str
    target_type: str
    target_id: uuid.UUID | None = None
    occurred_at: datetime
    request_id: str | None = None
    reason: str | None = None
    details: dict = {}
    ip_address: str | None = None
    user_agent_abridged: str | None = None
