"""Shared Django/DRF fixtures for the API test suite.

Tests run against real PostgreSQL so row locking, partial constraints and the
append-only triggers are exercised. All identities, coordinates and images are
synthetic. Sessions use Django's real session/CSRF stack; only the test client's
convenience flag disables CSRF for tests that are not specifically about CSRF.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

from corn.rate_limit import reset_for_tests as reset_rate_limit
from corn.services import auth as auth_service
from corn.services import inventory as inventory_service
from corn.storage import reset_storage_for_tests

ADMIN_PASSWORD = "Sup3rAdminPass!"
DISTRIBUTOR_PASSWORD = "Str0ngDistribPass!"


@pytest.fixture(autouse=True)
def _reset_process_state():
    reset_rate_limit()
    reset_for_tests_storage_files()
    yield
    reset_rate_limit()


def reset_for_tests_storage_files() -> None:
    root = Path(settings.LOCAL_STORAGE_DIR)
    if root.exists():
        for item in root.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    reset_storage_for_tests()


def json_request(client: Client, method: str, path: str, payload=None, **extra):
    kwargs = {"content_type": "application/json", **extra}
    if payload is not None and method.lower() not in {"get", "head"}:
        kwargs["data"] = json.dumps(payload)
    return getattr(client, method)(path, **kwargs)


class AuthClient:
    def __init__(self) -> None:
        self.client = Client()

    def login(self, email: str, password: str) -> dict:
        response = json_request(
            self.client, "post", "/api/v1/auth/login", {"email": email, "password": password}
        )
        assert response.status_code == 200, response.content.decode()
        return response.json()["user"]

    def create_admin(self, email: str = "admin@example.org", password: str = ADMIN_PASSWORD) -> dict:
        user = auth_service.create_first_admin(
            email=email, password=password, display_name="Ops"
        )
        inventory_service.ensure_core_org_rows(created_by=user.id)
        return self.login(email, password)

    def create_distributor(
        self, email: str = "dist1@example.org", name: str = "Field Distributor"
    ) -> dict:
        from corn.models import User

        User.objects.create_user(
            email=email,
            password=DISTRIBUTOR_PASSWORD,
            display_name=name,
            role="DISTRIBUTOR",
            is_active=True,
        )
        return self.login(email, DISTRIBUTOR_PASSWORD)


@pytest.fixture()
def auth() -> AuthClient:
    return AuthClient()


@pytest.fixture()
def csrf_client() -> Client:
    return Client(enforce_csrf_checks=True)


@pytest.fixture()
def org_factory(auth: AuthClient):
    """Create the standard synthetic org through real HTTP API calls."""

    def factory(**overrides) -> dict:
        admin_auth = AuthClient()
        dist_auth = AuthClient()
        admin_user = admin_auth.create_admin()
        dist_user = dist_auth.create_distributor(
            email=overrides.get("dist_email", "dist1@example.org"), name="Field Distributor"
        )
        admin = admin_auth.client
        dist = dist_auth.client

        campaign_id = None
        if overrides.get("campaign"):
            campaign = json_request(
                admin,
                "post",
                "/api/v1/campaigns",
                {
                    "name": "Rains Distribution",
                    "reference_code": "RAINS-1",
                    "timezone": "Africa/Juba",
                    "status": "ACTIVE",
                },
            )
            assert campaign.status_code == 201, campaign.content.decode()
            campaign_id = campaign.json()["id"]

        site_resp = json_request(
            admin,
            "post",
            "/api/v1/sites",
            {
                "name": "North Depot",
                "site_code": "ND-01",
                "latitude": "12.551800",
                "longitude": "15.100000",
                "geofence_radius_m": 200,
            },
        )
        assert site_resp.status_code == 201, site_resp.content.decode()
        site = site_resp.json()

        assign_resp = json_request(
            admin,
            "post",
            "/api/v1/assignments",
            {
                "site_id": site["id"],
                "campaign_id": campaign_id,
                "distributor_user_id": dist_user["id"],
                "target_quantity": "150",
                "unit": "KG",
            },
        )
        assert assign_resp.status_code == 201, assign_resp.content.decode()
        assignment = assign_resp.json()

        receipt_resp = json_request(
            admin,
            "post",
            "/api/v1/inventory/receipts",
            {
                "quantity": "500",
                "unit": "KG",
                "source_reference": "warehouse-load-2026-10",
            },
            HTTP_IDEMPOTENCY_KEY="test-receipt-1",
        )
        assert receipt_resp.status_code == 201, receipt_resp.content.decode()

        alloc_resp = json_request(
            admin,
            "post",
            "/api/v1/inventory/allocations",
            {
                "distributor_user_id": dist_user["id"],
                "quantity": "100",
                "unit": "KG",
            },
            HTTP_IDEMPOTENCY_KEY="test-alloc-1",
        )
        assert alloc_resp.status_code == 201, alloc_resp.content.decode()

        return {
            "admin_client": admin,
            "dist_client": dist,
            "admin_user": admin_user,
            "dist_user": dist_user,
            "site": site,
            "assignment": assignment,
            "distributor_user_id": dist_user["id"],
            "campaign_id": campaign_id,
            "auth": auth,
            "dist_auth": dist_auth,
        }

    return factory


def upload_png(client: Client, *, color: tuple[int, int, int] = (44, 95, 45)) -> dict:
    """Create an upload intent and PUT a unique synthetic PNG to it."""
    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    image = Image.new("RGB", (8, 8), color)
    image.save(buffer, format="PNG")
    return upload_bytes(client, buffer.getvalue(), "image/png")


def upload_bytes(client: Client, data: bytes, content_type: str) -> dict:
    """Upload arbitrary bytes through a real intent; validation is API-side."""
    intent = json_request(
        client,
        "post",
        "/api/v1/evidence/upload-intents",
        {"content_type": content_type, "purpose": "DISTRIBUTION_EVIDENCE"},
    )
    assert intent.status_code == 201, intent.content.decode()
    body = intent.json()
    upload = client.put(
        body["upload_url"],
        data=data,
        content_type=content_type,
    )
    assert upload.status_code == 204, upload.content.decode()
    return {
        "intent_id": body["intent_id"],
        "capture_source": "CAMERA",
    }


def submit_delivery(
    client: Client,
    *,
    assignment_id: str,
    quantity: str,
    evidence: dict,
    idempotency_key: str,
    latitude: str = "12.551900",
    longitude: str = "15.100100",
    accuracy: str = "8",
    timestamp: str | None = None,
    include_location: bool = True,
):
    if timestamp is None:
        from datetime import UTC, datetime

        timestamp = datetime.now(UTC).isoformat()
    payload = {
        "assignment_id": assignment_id,
        "quantity": quantity,
        "unit": "KG",
        "evidence": [evidence],
    }
    if include_location:
        payload["location"] = {
            "latitude": latitude,
            "longitude": longitude,
            "accuracy_m": accuracy,
            "timestamp": timestamp,
        }
    return json_request(
        client,
        "post",
        "/api/v1/deliveries",
        payload,
        HTTP_IDEMPOTENCY_KEY=idempotency_key,
    )
