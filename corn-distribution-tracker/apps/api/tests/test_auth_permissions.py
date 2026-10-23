"""Authentication, session/CSRF, invitation and RBAC tests."""

from __future__ import annotations

import json
import uuid
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from corn.errors import AppError
from corn.models import User
from corn.services import auth as auth_service
from tests.conftest import ADMIN_PASSWORD, AuthClient, json_request

pytestmark = pytest.mark.django_db


def test_unauthenticated_requests_are_rejected():
    client = Client()
    for path in (
        "/api/v1/campaigns",
        "/api/v1/sites",
        "/api/v1/deliveries",
        "/api/v1/inventory/summary",
        "/api/v1/analytics/overview",
        "/api/v1/audit/events",
        "/api/v1/admin/distributors",
    ):
        response = client.get(path)
        assert response.status_code == 401, (path, response.status_code)
        assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_distributor_admin_endpoints_are_forbidden(org_factory):
    org = org_factory()
    for method, path in (
        ("get", "/api/v1/admin/distributors"),
        ("get", "/api/v1/audit/events"),
        ("get", "/api/v1/analytics/distributors"),
        ("post", "/api/v1/campaigns"),
    ):
        response = json_request(org["dist_client"], method, path, {})
        assert response.status_code == 403, (path, response.content)
        assert response.json()["error"]["code"] == "FORBIDDEN"


def test_distributor_cannot_read_other_scope(org_factory):
    org = org_factory()
    foreign = uuid.uuid4()
    for path in (
        f"/api/v1/assignments/{foreign}",
        f"/api/v1/deliveries/{foreign}",
        f"/api/v1/evidence/{foreign}/view-url",
        f"/api/v1/inventory/accounts/{foreign}/ledger",
    ):
        response = org["dist_client"].get(path)
        assert response.status_code == 404, (path, response.content)
    rows = org["dist_client"].get("/api/v1/deliveries").json()
    assert rows["items"] == []


def test_distributor_assignment_site_summary_hides_admin_notes(org_factory):
    org = org_factory()
    response = org["dist_client"].get("/api/v1/distributors/me/assignments")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    item = items[0]
    assert item["assignment_id"] == org["assignment"]["id"]
    assert item["site"]["id"] == org["site"]["id"]
    assert item["site"]["notes"] is None
    assert item["site"]["created_at"]
    assert item["target_kg"] == "150.000"
    assert item["remaining_target_kg"] == "150.000"


def test_login_rate_limit_locks_repeated_failures():
    client = Client()
    for _ in range(10):
        response = json_request(
            client, "post", "/api/v1/auth/login", {"email": "nobody@example.org", "password": "wrong"}
        )
        assert response.status_code == 401
    locked = json_request(
        client, "post", "/api/v1/auth/login", {"email": "nobody@example.org", "password": "wrong"}
    )
    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "RATE_LIMITED"
    assert locked["Retry-After"]


def test_locked_account_returns_retry_window(auth: AuthClient):
    auth.create_admin()
    User.objects.filter(email="admin@example.org").update(
        locked_until=timezone.now() + timedelta(minutes=10)
    )
    response = json_request(
        Client(),
        "post",
        "/api/v1/auth/login",
        {"email": "admin@example.org", "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 429
    assert response["Retry-After"]
    assert response.json()["error"]["details"][0]["retry_after"] > 0


def test_successful_logins_do_not_consume_failure_rate_limit(auth: AuthClient):
    """A shared/NAT IP is only throttled for failures, not normal sign-ins."""
    auth.create_admin()
    for _ in range(12):
        response = json_request(
            auth.client,
            "post",
            "/api/v1/auth/login",
            {"email": "admin@example.org", "password": ADMIN_PASSWORD},
        )
        assert response.status_code == 200, response.content


def test_session_login_me_logout_and_csrf(csrf_client: Client):
    admin = AuthClient()
    admin.create_admin()
    unauthorized = csrf_client.get("/api/v1/auth/me")
    assert unauthorized.status_code == 401

    login = json_request(
        csrf_client,
        "post",
        "/api/v1/auth/login",
        {"email": "admin@example.org", "password": ADMIN_PASSWORD},
    )
    assert login.status_code == 200, login.content
    body = login.json()
    assert "access_token" not in body
    assert body["user"]["role"] == "ADMIN"
    assert csrf_client.cookies["sessionid"].value
    csrf_token = csrf_client.cookies["csrftoken"].value
    assert csrf_token

    me = csrf_client.get("/api/v1/auth/me")
    assert me.status_code == 200 and me.json()["email"] == "admin@example.org"

    # Unsafe session-authenticated requests need the double-submit token.
    missing = csrf_client.post(
        "/api/v1/auth/logout", data="{}", content_type="application/json"
    )
    assert missing.status_code == 403
    assert missing.json()["error"]["code"] == "FORBIDDEN"

    logout = csrf_client.post(
        "/api/v1/auth/logout",
        data="{}",
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert logout.status_code == 200
    assert csrf_client.get("/api/v1/auth/me").status_code == 401


def test_csrf_bootstrap_endpoint_sets_cookie(client: Client):
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    payload = response.json()
    token = payload["csrf_token"]
    assert token
    # Django returns a masked token while the cookie holds the secret; both are
    # needed, and neither is an authentication credential on its own.
    assert client.cookies["csrftoken"].value


def test_password_reset_response_is_generic(csrf_client: Client):
    AuthClient().create_admin()
    known = json_request(
        csrf_client, "post", "/api/v1/auth/forgot-password", {"email": "admin@example.org"}
    )
    unknown = json_request(
        csrf_client, "post", "/api/v1/auth/forgot-password", {"email": "ghost@example.org"}
    )
    assert known.status_code == unknown.status_code == 200
    assert known.json()["message"] == unknown.json()["message"]


def test_invitation_acceptance_is_one_time(org_factory):
    org = org_factory()
    invitation = json_request(
        org["admin_client"],
        "post",
        "/api/v1/admin/users/invitations",
        {
            "email": "new.field@example.org",
            "display_name": "New Field",
            "role": "DISTRIBUTOR",
        },
    )
    assert invitation.status_code == 201, invitation.content
    token = invitation.json()["invite_token"]
    accept = json_request(
        org["admin_client"],
        "post",
        "/api/v1/auth/accept-invitation",
        {"token": token, "password": "An0therGoodPass!"},
    )
    assert accept.status_code == 200, accept.content
    assert accept.json()["role"] == "DISTRIBUTOR"
    reused = json_request(
        org["admin_client"],
        "post",
        "/api/v1/auth/accept-invitation",
        {"token": token, "password": "An0therGoodPass!"},
    )
    assert reused.status_code == 400


def test_invitation_token_is_hashed_and_never_returned_in_list(org_factory):
    org = org_factory()
    invitation = json_request(
        org["admin_client"],
        "post",
        "/api/v1/admin/users/invitations",
        {"email": "hashcheck@example.org", "display_name": "Hash Check"},
    )
    assert invitation.status_code == 201
    token = invitation.json()["invite_token"]
    listed = org["admin_client"].get("/api/v1/admin/users/invitations").json()
    assert listed
    assert all("invite_token" not in row for row in listed)
    from corn.models import Invitation

    row = Invitation.objects.get(email="hashcheck@example.org")
    assert row.token_hash != token


def test_no_public_bootstrap_or_role_elevation(org_factory):
    org = org_factory()
    assert (
        org["dist_client"].post(
            "/api/v1/admin/bootstrap",
            data=json.dumps({"email": "x@example.org", "password": "longpassword1"}),
            content_type="application/json",
        ).status_code
        in (404, 405)
    )
    assert (
        json_request(
            org["dist_client"],
            "post",
            "/api/v1/auth/accept-invitation",
            {"token": "made-up-token-value", "password": "WhateverPass1!"},
        ).status_code
        == 400
    )


def test_first_admin_rejects_invalid_email_and_second_admin():
    with pytest.raises(AppError, match="valid email"):
        auth_service.create_first_admin(
            email="not-an-email", password="Synthetic-Passw0rd!42", display_name=None
        )
    auth_service.create_first_admin(
        email="admin@example.org", password="Synthetic-Passw0rd!42", display_name=None
    )
    with pytest.raises(AppError, match="already exists"):
        auth_service.create_first_admin(
            email="other@example.org", password="Synthetic-Passw0rd!42", display_name=None
        )


def test_deactivation_revokes_sessions(org_factory):
    org = org_factory()
    target_id = org["distributor_user_id"]
    assert org["dist_client"].get("/api/v1/deliveries").status_code == 200
    deactivate = org["admin_client"].post(f"/api/v1/admin/distributors/{target_id}/deactivate")
    assert deactivate.status_code == 200, deactivate.content
    assert deactivate.json()["is_active"] is False
    # The database-backed session was deleted, not merely role-flagged.
    assert org["dist_client"].get("/api/v1/deliveries").status_code == 401
    assert not User.objects.get(id=target_id).is_active
