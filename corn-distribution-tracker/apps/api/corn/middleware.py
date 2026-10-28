"""Request context, origin validation and security headers."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse

from .errors import FORBIDDEN, error_body

logger = logging.getLogger("corn.request")

_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class RequestContextMiddleware:
    """Attach a sanitized request id, log one safe line per request."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        raw = request.headers.get("x-request-id", "")
        request_id = "".join(c for c in raw if c.isalnum() or c in "-_")[:64] or uuid.uuid4().hex
        request.request_id = request_id  # type: ignore[attr-defined]
        started = time.perf_counter()
        try:
            response = self.get_response(request)
        except Exception:
            logger.exception(
                "request_failed method=%s path=%s request_id=%s",
                request.method,
                request.path,
                request_id,
            )
            raise
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response["X-Request-ID"] = request_id
        logger.info(
            "request method=%s path=%s status=%s duration_ms=%s request_id=%s",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response


class OriginCheckMiddleware:
    """Check Origin/Referer on unsafe requests.

    This complements Django's session/CSRF protections and covers the small
    number of unauthenticated POSTs (login, reset, invitation acceptance). It is
    not a replacement for HTTPS at the edge.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.allowed = {origin.rstrip("/") for origin in settings.CORS_ALLOWED_ORIGINS}
        if settings.DEBUG:
            for host in ("http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"):
                self.allowed.add(host)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.method in _UNSAFE_METHODS:
            origin = request.headers.get("origin")
            if origin:
                origin = origin.rstrip("/")
            else:
                # Some older clients omit Origin but still send Referer. Check
                # its origin when present; requests with neither header still
                # pass through Django's CSRF/session protection.
                referer = request.headers.get("referer")
                if referer:
                    from urllib.parse import urlsplit

                    parsed = urlsplit(referer)
                    origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
            if origin:
                request_origin = f"{request.scheme}://{request.get_host()}".rstrip("/")
                if origin not in self.allowed and origin != request_origin:
                    return JsonResponse(
                        error_body(
                            FORBIDDEN,
                            "Origin not allowed.",
                            getattr(request, "request_id", None),
                        ),
                        status=403,
                    )
        return self.get_response(request)


class SecurityHeadersMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("Referrer-Policy", "same-origin")
        response.setdefault("X-Frame-Options", "DENY")
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        response.setdefault(
            "Permissions-Policy",
            "geolocation=(self), camera=(self), microphone=(), payment=(), usb=()",
        )
        if request.path.startswith(settings.API_V1_PREFIX):
            response.setdefault("Cache-Control", "no-store")
        return response
