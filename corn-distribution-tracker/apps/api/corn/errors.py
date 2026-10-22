"""Canonical API error envelope and DRF exception handling.

The response shape is preserved from the original contract:

    {"error": {"code": "...", "message": "...", "request_id": "...", "details": []}}

Human-safe messages only: no SQL, stack traces, tokens, storage keys or object
names. Machine codes are stable so the SPA and operators can switch on them.
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from rest_framework import status
from rest_framework.exceptions import APIException, NotAuthenticated, PermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.views import exception_handler as drf_default_handler

logger = logging.getLogger("corn.errors")

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


class AppError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = VALIDATION_ERROR

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        self.message = message
        self.error_code = code or self.default_code
        if status_code is not None:
            self.status_code = status_code
        self.details = details or []
        super().__init__(detail=message, code=self.error_code)


class AuthRequiredError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = UNAUTHENTICATED


class UnprocessableEntityError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = VALIDATION_ERROR


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = FORBIDDEN


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = NOT_FOUND


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    default_code = CONFLICT


class RateLimitedError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_code = RATE_LIMITED

    def __init__(
        self,
        message: str = "Too many attempts; try again later.",
        *,
        retry_after: int = 0,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        self.retry_after = max(retry_after, 0)
        super().__init__(
            message,
            code=RATE_LIMITED,
            details=details or [{"retry_after": self.retry_after}] if self.retry_after else details,
        )


def error_body(
    code: str,
    message: str,
    request_id: str | None,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "details": details or [],
        }
    }


def _flatten_details(data: Any, prefix: str = "") -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    if isinstance(data, dict):
        for key, value in data.items():
            field = f"{prefix}.{key}" if prefix else str(key)
            details.extend(_flatten_details(value, field))
    elif isinstance(data, (list, tuple)):
        for index, value in enumerate(data):
            field = f"{prefix}.{index}" if prefix else str(index)
            details.extend(_flatten_details(value, field))
    else:
        details.append({"field": prefix or "request", "message": str(data)})
    return details


def drf_exception_handler(exc: Exception, context: dict[str, Any]):
    request = context.get("request")
    request_id = getattr(request, "request_id", None) if request is not None else None

    if isinstance(exc, AppError):
        response = JsonResponse(
            error_body(exc.error_code, exc.message, request_id, exc.details),
            status=exc.status_code,
        )
        if isinstance(exc, RateLimitedError) and exc.retry_after:
            response["Retry-After"] = str(exc.retry_after)
        return response

    if isinstance(exc, DRFValidationError):
        details = _flatten_details(exc.detail)
        return JsonResponse(
            error_body(VALIDATION_ERROR, "Request validation failed.", request_id, details),
            status=422,
        )

    if isinstance(exc, (NotAuthenticated, PermissionDenied)) and not isinstance(exc, AppError):
        code = UNAUTHENTICATED if isinstance(exc, NotAuthenticated) else FORBIDDEN
        message = (
            "Authentication required."
            if code == UNAUTHENTICATED
            else "You do not have permission to do that."
        )
        status_code = 401 if code == UNAUTHENTICATED else 403
        return JsonResponse(error_body(code, message, request_id), status=status_code)

    if isinstance(exc, ObjectDoesNotExist):
        return JsonResponse(error_body(NOT_FOUND, "Resource not found.", request_id), status=404)

    response = drf_default_handler(exc, context)
    if response is not None:
        code = getattr(exc, "default_code", "ERROR").upper()
        detail = getattr(exc, "detail", None)
        if isinstance(detail, dict):
            details = _flatten_details(detail)
            message = "Request failed."
        elif isinstance(detail, list):
            details = _flatten_details(detail)
            message = "Request failed."
        else:
            details = []
            message = str(detail) if detail else "Request failed."
        response.data = error_body(code, message, request_id, details)
        return response

    logger.exception("unhandled_error request_id=%s", request_id)
    return JsonResponse(
        error_body(INTERNAL_ERROR, "Unexpected server error.", request_id),
        status=500,
    )


def json_404(request, exception=None) -> JsonResponse:
    return JsonResponse(
        error_body(NOT_FOUND, "Resource not found.", getattr(request, "request_id", None)),
        status=404,
    )


def json_500(request) -> JsonResponse:
    return JsonResponse(
        error_body(INTERNAL_ERROR, "Unexpected server error.", getattr(request, "request_id", None)),
        status=500,
    )
