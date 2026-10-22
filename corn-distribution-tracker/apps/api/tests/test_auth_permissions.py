"""Auth + RBAC + session tests (adversarial ID checks per ACCEPTANCE_CRITERIA)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.errors import AppError
from app.core.security import hash_refresh_token
from app.models import RefreshToken
from app.services import auth_service
from tests.conftest import _make_session


def test_unauthenticated_requests_are_rejected(client: TestClient):
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
        body = response.json()
        assert body["error"]["code"] in {"UNAUTHENTICATED", "NOT_FOUND"}


def test_distributor_admin_endpoints_are_forbidden(org_factory, client: TestClient):
    org = org_factory()
    response = client.get("/api/v1/admin/distributors", headers=org["headers_dist"])
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_distributor_cannot_read_other_distributor_scope(org_factory, client: TestClient):
    org = org_factory()
    other = uuid.uuid4()  # fabricated foreign ids

    # Foreign assignment detail -> 404, not a leak of contents
    r = client.get(f"/api/v1/assignments/{other}", headers=org["headers_dist"])
    assert r.status_code == 404

    # Foreign delivery record -> 404
    r = client.get(f"/api/v1/deliveries/{other}", headers=org["headers_dist"])
    assert r.status_code == 404

    # Foreign delivery evidence view url -> 404
    r = client.get(f"/api/v1/evidence/{other}/view-url", headers=org["headers_dist"])
    assert r.status_code == 404

    # Foreign stock account ledger -> 404
    r = client.get(f"/api/v1/inventory/accounts/{other}/ledger", headers=org["headers_dist"])
    assert r.status_code == 404

    # Deliveries list never contains other distributors' rows for a fresh distributor.
    # (org distributor has no records yet)
    r = client.get("/api/v1/deliveries", headers=org["headers_dist"])
    assert r.status_code == 200 and r.json()["items"] == []


def test_admin_requests_shipper_ids_are_erroring_not_leaking(org_factory, client: TestClient):
    org = org_factory()
    # Admin hitting a non-existent assignment gets 404 (not 403) — same shape.
    r = client.get(f"/api/v1/assignments/{uuid.uuid4()}", headers=org["headers_admin"])
    assert r.status_code == 404


def test_distributor_assignment_list_returns_complete_site_summary(org_factory, client: TestClient):
    """Regression: the nested site must satisfy SiteOut or every distributor 500s."""
    org = org_factory()
    r = client.get("/api/v1/distributors/me/assignments", headers=org["headers_dist"])
    assert r.status_code == 200, r.text
    assert len(r.json()) == 1
    item = r.json()[0]
    assert item["assignment_id"] == org["assignment"]["id"]
    site = item["site"]
    assert site["id"] == org["site"]["id"]
    assert site["is_active"] is True
    assert site["created_at"]
    assert site["latitude"] == org["site"]["latitude"]
    assert site["longitude"] == org["site"]["longitude"]
    # Admin-internal notes must never leak to a distributor response.
    assert site["notes"] is None


def test_login_rate_limit_locks_repeated_failures(client: TestClient):
    for _ in range(10):
        r = client.post("/api/v1/auth/login", json={"email": "nobody@example.org", "password": "wrong"})
        assert r.status_code == 401
    locked = client.post("/api/v1/auth/login", json={"email": "nobody@example.org", "password": "wrong"})
    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "RATE_LIMITED"


def test_refresh_rotation_and_reuse_detection(client: TestClient, org_factory):
    org_factory()  # bootstraps admin@example.org
    # login obtains an HttpOnly refresh cookie
    login = client.post(
        "/api/v1/auth/login", json={"email": "admin@example.org", "password": "Sup3rAdminPass!"}
    )
    assert login.status_code == 200
    stale = login.cookies.get("refresh_token")
    assert stale, "login must set the refresh_token cookie"

    refresh = client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 200

    # Replay the revoked login token: reuse detection must 401 and revoke the family.
    client.cookies.set("refresh_token", stale)
    reused = client.post("/api/v1/auth/refresh")
    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "UNAUTHENTICATED"

    db = _make_session()
    try:
        reused_row = db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(stale))
        )
        assert reused_row is not None and reused_row.revoked_at is not None, "replayed token must be revoked"
        family_rows = list(
            db.scalars(select(RefreshToken).where(RefreshToken.family_id == reused_row.family_id))
        )
        assert family_rows
        assert all(r.revoked_at is not None for r in family_rows), "reuse must revoke the whole family"
    finally:
        db.close()


def test_logout_revokes_session(client: TestClient, org_factory):
    org_factory()  # bootstraps admin@example.org
    client.post("/api/v1/auth/login", json={"email": "admin@example.org", "password": "Sup3rAdminPass!"})
    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 200
    after = client.post("/api/v1/auth/refresh")
    assert after.status_code == 401


def test_generic_password_reset_response_does_not_reveal_accounts(client: TestClient):
    r1 = client.post("/api/v1/auth/forgot-password", json={"email": "admin@example.org"})
    r2 = client.post("/api/v1/auth/forgot-password", json={"email": "ghost@example.org"})
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["message"] == r2.json()["message"]


def test_invitation_flow_accept_expiry(org_factory, client: TestClient):
    org = org_factory()  # the inviting admin's headers come from the factory
    inv = client.post(
        "/api/v1/admin/users/invitations",
        json={"email": "new.field@example.org", "display_name": "New Field", "role": "DISTRIBUTOR"},
        headers=org["headers_admin"],
    )
    assert inv.status_code == 201, inv.text
    token = inv.json()["invite_token"]

    accept = client.post(
        "/api/v1/auth/accept-invitation", json={"token": token, "password": "An0therGoodPass!"}
    )
    assert accept.status_code == 200, accept.text
    reused = client.post(
        "/api/v1/auth/accept-invitation", json={"token": token, "password": "An0therGoodPass!"}
    )
    assert reused.status_code == 400


def test_no_public_make_me_admin(org_factory, client: TestClient):
    # There is no bootstrap HTTP endpoint; the check below documents it stays absent.
    r1 = client.post(
        "/api/v1/auth/accept-invitation", json={"token": "made-it-up", "password": "WhateverPass1!"}
    )
    assert r1.status_code == 400
    # No /admin/bootstrap route is exposed.
    r2 = client.post("/api/v1/admin/bootstrap", json={"email": "x@example.org", "password": "longpassword1"})
    assert r2.status_code in (404, 405)


def test_first_admin_bootstrap_rejects_unusable_email():
    # The login schema uses pydantic EmailStr, which rejects special-use TLDs.
    # The CLI must not create an account that can never authenticate.
    db = _make_session()
    try:
        with pytest.raises(AppError, match="valid email"):
            auth_service.create_first_admin(
                db,
                email="admin@example.test",
                password="Synthetic-Passw0rd!42",
                display_name=None,
            )
    finally:
        db.close()
