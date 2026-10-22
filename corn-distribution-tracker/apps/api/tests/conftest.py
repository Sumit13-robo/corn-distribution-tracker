"""Shared test fixtures: isolated schema, truncation, client with auth helpers.

Tests run against a real PostgreSQL database (TEST_DATABASE_URL) so ledger row
locking, partial indexes and append-only triggers are exercised for real.
Synthetic data only - never real personal data or geotagged images.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator

# Configure environment BEFORE importing app modules.
_TEST_DB = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://corn:corn@localhost:5432/corn_tracker_test"
)
_TMP = tempfile.mkdtemp(prefix="corn-evidence-")
os.environ.update(
    {
        "APP_ENV": "test",
        "DATABASE_URL": _TEST_DB,
        "STORAGE_MODE": "local",
        "LOCAL_STORAGE_DIR": _TMP,
        "SECRET_KEY": "test-secret-not-for-production-only",
        "CORS_ALLOWED_ORIGINS": "http://localhost:5173",
        "COOKIE_SECURE": "false",
        "MAX_EVIDENCE_UPLOAD_BYTES": "1048576",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.rate_limit import reset_for_tests as reset_rate_limit  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services import auth_service  # noqa: E402


def _truncate_all(db) -> None:
    db.execute(
        text(
            "DO $$ DECLARE r RECORD; BEGIN FOR r IN (SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename <> 'alembic_version') LOOP "
            "EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' CASCADE'; END LOOP; END $$;"
        )
    )
    db.commit()


@pytest.fixture(autouse=True)
def _clean_database():
    """Truncate the whole test schema between tests for full isolation."""
    engine = get_engine()
    conn = engine.connect()
    try:
        conn.execute(
            text(
                "DO $$ DECLARE r RECORD; BEGIN FOR r IN (SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename <> 'alembic_version') LOOP "
                "EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' CASCADE'; END LOOP; END $$;"
            )
        )
        conn.commit()
    finally:
        conn.close()
    reset_rate_limit()
    yield
    reset_rate_limit()


@pytest.fixture()
def client() -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client


class AuthQuestions:
    def __init__(self, client: TestClient):
        self.client = client

    def create_admin(self, email: str = "admin@example.org", password: str = "Sup3rAdminPass!") -> str:
        db = _make_session()
        try:
            auth_service.create_first_admin(db, email=email, password=password, display_name="Ops")
            auth_service.ensure_core_org_rows(db)
            db.commit()
        finally:
            db.close()
        return self.login(email, password)

    def create_distributor(self, email: str = "dist1@example.org", name: str = "Field Distributor") -> str:
        from app.core.security import hash_password
        from app.models import User

        db = _make_session()
        try:
            user = User(
                email_normalized=email,
                display_name=name,
                role="DISTRIBUTOR",
                is_active=True,
                password_hash=hash_password("Str0ngDistribPass!"),
            )
            db.add(user)
            db.commit()
        finally:
            db.close()
        return self.login(email, "Str0ngDistribPass!")

    def login(self, email: str, password: str) -> str:
        response = self.client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        return response.json()["access_token"]

    def bearer(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}


def _make_session():
    from app.db.session import get_session_factory

    return get_session_factory()()


@pytest.fixture()
def auth(client: TestClient) -> AuthQuestions:
    return AuthQuestions(client)


@pytest.fixture()
def org_factory(auth: AuthQuestions):
    """Create the standard synthetic org: admin + distributor + campaign + site + assignment + stock."""
    created: dict = {}

    def factory(**overrides) -> dict:
        admin_token = auth.create_admin()
        dist_token = auth.create_distributor(
            email=overrides.get("dist_email", "dist1@example.org"), name="Field Distributor"
        )
        headers_admin = auth.bearer(admin_token)
        headers_dist = auth.bearer(dist_token)

        campaign = overrides.get("campaign")
        if campaign:
            resp = auth.client.post(
                "/api/v1/campaigns",
                json={
                    "name": "Rains Distribution",
                    "reference_code": "RAINS-1",
                    "timezone": "Africa/Juba",
                    "status": "ACTIVE",
                },
                headers=headers_admin,
            )
            campaign_id = resp.json()["id"]
        else:
            campaign_id = None

        site_resp = auth.client.post(
            "/api/v1/sites",
            json={
                "name": "North Depot",
                "site_code": "ND-01",
                "latitude": "12.551800",
                "longitude": "15.100000",
                "geofence_radius_m": 200,
            },
            headers=headers_admin,
        )
        assert site_resp.status_code == 201, site_resp.text
        site = site_resp.json()

        users_resp = auth.client.get("/api/v1/admin/distributors", headers=headers_admin)
        distributor_user_id = users_resp.json()["items"][0]["id"]

        assign_resp = auth.client.post(
            "/api/v1/assignments",
            json={
                "site_id": site["id"],
                "campaign_id": campaign_id,
                "distributor_user_id": distributor_user_id,
                "target_quantity": "150",
                "unit": "KG",
            },
            headers=headers_admin,
        )
        assert assign_resp.status_code == 201, assign_resp.text
        assignment = assign_resp.json()

        receipt_resp = auth.client.post(
            "/api/v1/inventory/receipts",
            json={"quantity": "500", "unit": "KG", "source_reference": "warehouse-load-2026-10"},
            headers={**headers_admin, "Idempotency-Key": "test-receipt-1"},
        )
        assert receipt_resp.status_code == 201, receipt_resp.text

        alloc_resp = auth.client.post(
            "/api/v1/inventory/allocations",
            json={"distributor_user_id": distributor_user_id, "quantity": "100", "unit": "KG"},
            headers={**headers_admin, "Idempotency-Key": "test-alloc-1"},
        )
        assert alloc_resp.status_code == 201, alloc_resp.text

        created.update(
            admin_token=admin_token,
            dist_token=dist_token,
            headers_admin=headers_admin,
            headers_dist=headers_dist,
            site=site,
            assignment=assignment,
            distributor_user_id=distributor_user_id,
            campaign_id=campaign_id,
            auth=auth,
        )
        return created

    return factory
