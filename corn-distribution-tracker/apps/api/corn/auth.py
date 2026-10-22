"""Authentication helpers and DRF permissions."""

from __future__ import annotations

from rest_framework.authentication import SessionAuthentication as DRFSessionAuthentication
from rest_framework.permissions import BasePermission


class SessionAuthentication(DRFSessionAuthentication):
    """Django session auth with an explicit 401 challenge for anonymous requests.

    DRF enforces CSRF for authenticated unsafe requests (SessionAuthentication).
    The SPA sends the CSRF cookie value in X-CSRFToken. Login and recovery
    endpoints are unauthenticated and are additionally origin-checked by
    middleware.
    """

    def authenticate_header(self, request) -> str:
        return "Session"


class IsAdminRole(BasePermission):
    message = "Administrator role required."

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and getattr(user, "role", None) == "ADMIN")


class IsDistributorRole(BasePermission):
    message = "This endpoint is for distributors."

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and getattr(user, "role", None) == "DISTRIBUTOR")
