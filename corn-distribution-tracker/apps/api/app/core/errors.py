"""Application error types and the canonical error response shape.

API_CONTRACT: {"error":{"code":"VALIDATION_ERROR","message":"...","request_id":"...","details":[]}}
Machine codes are stable: VALIDATION_ERROR, UNAUTHENTICATED, FORBIDDEN, NOT_FOUND,
CONFLICT, INSUFFICIENT_STOCK, ILLEGAL_STATE, DUPLICATE, RATE_LIMITED, INTERNAL_ERROR,
REASON_REQUIRED. Messages are human-safe: no SQL, stack traces, tokens or storage keys.
"""

from __future__ import annotations

from typing import Any

VALIDATION_ERROR = "VALIDATION_ERROR"
UNAUTHENTICATED = "UNAUTHENTICATED"
FORBIDDEN = "FORBIDDEN"
NOT_FOUND = "NOT_FOUND"
CONFLICT = "CONFLICT"
INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK"
ILLEGAL_STATE = "ILLEGAL_STATE"
DUPLICATE = "DUPLICATE"
RATE_LIMITED = "RATE_LIMITED"
REASON_REQUIRED = "REASON_REQUIRED"
INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    status_code = 400
    code = "VALIDATION_ERROR"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.details = details or []
        super().__init__(message)


class AuthRequiredError(AppError):
    status_code = 401
    code = UNAUTHENTICATED


class UnprocessableEntityError(AppError):
    """User-supplied content is syntactically valid JSON but semantically invalid."""

    status_code = 422
    code = VALIDATION_ERROR


class ForbiddenError(AppError):
    status_code = 403
    code = FORBIDDEN


class NotFoundError(AppError):
    status_code = 404
    code = NOT_FOUND


class ConflictError(AppError):
    status_code = 409
    code = CONFLICT


class RateLimitedError(AppError):
    status_code = 429
    code = RATE_LIMITED
