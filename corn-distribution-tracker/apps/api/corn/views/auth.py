"""Authentication and account lifecycle endpoints (Django session auth)."""

from __future__ import annotations

from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.db import transaction
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ..auth import IsAdminRole
from ..models import Invitation
from ..presenters import user_out
from ..serializers import (
    AcceptInvitationSerializer,
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    InvitationCreateSerializer,
    LoginSerializer,
    ResetPasswordSerializer,
)
from ..services import auth as auth_service
from ..services.audit import client_ip
from .helpers import response_ctx, set_csrf_cookie


def _ip_key(request) -> str:
    return (client_ip(request._request) or "unknown")[:64]


def _invitation_payload(invite: Invitation, *, raw_token: str | None = None) -> dict:
    from ..presenters import iso

    payload = {
        "id": str(invite.id),
        "email": invite.email,
        "display_name": invite.display_name,
        "role": invite.role,
        "expires_at": iso(invite.expires_at),
        "accepted_at": iso(invite.accepted_at),
        "revoked_at": iso(invite.revoked_at),
        "created_at": iso(invite.created_at),
    }
    if raw_token is not None:
        payload["invite_token"] = raw_token
    return payload


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    user = auth_service.authenticate_login(
        email=data["email"],
        password=data["password"],
        ctx=response_ctx(request),
        ip_key=_ip_key(request),
    )
    django_login(request._request, user, backend="django.contrib.auth.backends.ModelBackend")
    set_csrf_cookie(request._request)
    return Response({"user": user_out(user)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    set_csrf_cookie(request._request)
    return Response(user_out(request.user))


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def csrf(request):
    """Issue the CSRF cookie and return the token for cross-origin SPAs.

    This endpoint is safe/idempotent and unauthenticated; the token is not a
    secret by itself, but it is useless without the matching browser cookie.
    """
    token = set_csrf_cookie(request._request)
    return Response({"csrf_token": token})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    user = request.user
    auth_service.logout_audit(user=user, ctx=response_ctx(request))
    django_logout(request._request)
    response = Response({"status": "ok", "message": "Signed out."})
    response.delete_cookie("csrftoken")
    return response


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    with transaction.atomic():
        user = auth_service.change_password(
            user=request.user,
            current_password=data["current_password"],
            new_password=data["new_password"],
            ctx=response_ctx(request),
        )
    request._request.session.cycle_key()
    django_login(request._request, user, backend="django.contrib.auth.backends.ModelBackend")
    set_csrf_cookie(request._request)
    return Response({"status": "ok", "message": "Password updated."})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def forgot_password(request):
    serializer = ForgotPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    auth_service.request_password_reset(
        email=serializer.validated_data["email"],
        ctx=response_ctx(request),
        ip_key=_ip_key(request),
    )
    return Response(
        {
            "status": "ok",
            "message": (
                "Request recorded. An authorized operator can issue a one-time reset link "
                "through your organization's secure channel. This deployment does not send email."
            ),
        }
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def reset_password(request):
    serializer = ResetPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    with transaction.atomic():
        auth_service.reset_password(
            raw_token=data["token"], password=data["password"], ctx=response_ctx(request)
        )
    return Response(
        {"status": "ok", "message": "Password updated; all previous sessions were revoked."}
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def accept_invitation(request):
    serializer = AcceptInvitationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    with transaction.atomic():
        user = auth_service.accept_invitation(
            raw_token=data["token"],
            password=data["password"],
            display_name=data.get("display_name"),
            ctx=response_ctx(request),
        )
    return Response(user_out(user))


def _create_invitation(request):
    serializer = InvitationCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    with transaction.atomic():
        invite, raw_token = auth_service.create_invitation(
            admin=request.user,
            email=data["email"],
            display_name=data["display_name"],
            role=data["role"],
            ctx=response_ctx(request),
        )
    return Response(_invitation_payload(invite, raw_token=raw_token), status=201)


def _list_invitations(request):
    invites = Invitation.objects.order_by("-created_at")[:100]
    return Response([_invitation_payload(invite) for invite in invites])


@api_view(["GET", "POST"])
@permission_classes([IsAdminRole])
def invitations_collection(request):
    if request.method == "POST":
        return _create_invitation(request)
    return _list_invitations(request)
