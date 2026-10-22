"""FastAPI application entrypoint: middleware, error shape, readiness endpoints."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import AppError, RateLimitedError
from app.db.session import get_engine

logger = logging.getLogger("app")

SENSITIVE_HEADERS = {"authorization", "cookie", "x-api-key"}


def _error_body(code: str, message: str, details: list | None, request_id: str | None) -> dict:
    return {"error": {"code": code, "message": message, "request_id": request_id, "details": details or []}}


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    origins = [o for o in settings.cors_origin_list if o and o != "*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
        max_age=600,
    )

    @app.middleware("http")
    async def observability_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        # Sanitize incoming ids to safe charset/length.
        request_id = "".join(c for c in request_id if c.isalnum() or c in "-_")[:64] or uuid.uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("unhandled_error path=%s", request.url.path)
            response = JSONResponse(
                status_code=500,
                content=_error_body("INTERNAL_ERROR", "Unexpected server error.", None, request_id),
            )
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        logger.info(
            "request method=%s path=%s status=%s duration_ms=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        status = exc.status_code
        code = exc.code
        if isinstance(exc, RateLimitedError):
            code = "RATE_LIMITED"
        return JSONResponse(
            status_code=status,
            content=_error_body(code, exc.message, exc.details, getattr(request.state, "request_id", None)),
            headers={"Retry-After": str(getattr(exc, "retry_after_seconds", 0))}
            if isinstance(exc, RateLimitedError)
            else None,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(loc) for loc in err.get("loc", [])), "message": err.get("msg", "invalid")}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_error_body(
                "VALIDATION_ERROR",
                "Request validation failed.",
                details,
                getattr(request.state, "request_id", None),
            ),
        )

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=_error_body(
                "NOT_FOUND", "Resource not found.", None, getattr(request.state, "request_id", None)
            ),
        )

    @app.get("/health/live")
    async def health_live() -> JSONResponse:
        return JSONResponse({"status": "live"})

    @app.get("/health/ready")
    async def health_ready() -> JSONResponse:
        # Readiness tests dependencies safely, without exposing secrets or stack details.
        checks: dict[str, str] = {}
        try:
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "error"
        from app.services.storage_service import storage_health_probe

        probe = storage_health_probe(settings)
        checks["storage"] = "ok" if (probe.get("configured") or probe.get("writable")) else "error"
        status_code = 200 if all(v == "ok" for v in checks.values()) else 503
        return JSONResponse(
            {"status": "ready" if status_code == 200 else "degraded", "checks": checks},
            status_code=status_code,
        )

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
