"""Unauthenticated liveness and readiness probes (no secrets or stack traces)."""

from __future__ import annotations

import logging

from django.db import connection
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..storage import storage_health_probe

logger = logging.getLogger("corn.health")


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def live(request):
    return Response({"status": "ok"})


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def ready(request):
    checks: dict[str, str] = {}
    healthy = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except Exception:  # noqa: BLE001 - path must return 503, not details
        logger.exception("readiness database check failed")
        checks["database"] = "unavailable"
        healthy = False
    storage = storage_health_probe()
    storage_ok = storage.get("writable") is True or storage.get("reachable") is True
    checks["storage"] = "ok" if storage_ok else "unavailable"
    if not storage_ok:
        healthy = False
    return Response(
        {"status": "ok" if healthy else "degraded", "checks": checks},
        status=200 if healthy else 503,
    )
