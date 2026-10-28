"""Regression coverage for the 2026-10 remediation findings.

These tests exercise the exact failure modes found in the audit: cross-operation
idempotency collisions, reversal integrity, target-approval races, campaign and
site-stock scope leaks, direct-to-object-storage completion and proxy-header
spoofing. All data and images are synthetic.
"""

from __future__ import annotations

import threading
from decimal import Decimal
from io import BytesIO
from unittest.mock import MagicMock

import pytest
from django.conf import settings
from django.db import connection, transaction
from django.db.models import Sum
from django.test import Client, RequestFactory, override_settings
from PIL import Image

from corn.models import DistributionRecord, PhotoEvidence, StockAccount, StockMovement, UploadIntent
from corn.services.audit import client_ip
from corn.services.inventory import get_or_create_site_account
from corn.storage import S3StorageService, get_storage_service
from tests.conftest import (
    DISTRIBUTOR_PASSWORD,
    AuthClient,
    json_request,
    submit_delivery,
    upload_png,
)

pytestmark = pytest.mark.django_db


def central_account(client: Client) -> dict:
    summary = client.get("/api/v1/inventory/summary").json()
    return next(row for row in summary["accounts"] if row["account_type"] == "CENTRAL")


def distributor_account(client: Client) -> dict:
    summary = client.get("/api/v1/inventory/summary").json()
    return next(row for row in summary["accounts"] if row["account_type"] == "DISTRIBUTOR")


def approve(client: Client, record_id: str, *, key: str):
    return json_request(
        client,
        "post",
        f"/api/v1/deliveries/{record_id}/approve",
        {},
        HTTP_IDEMPOTENCY_KEY=key,
    )


def png_bytes(color: tuple[int, int, int] = (12, 34, 56)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), color).save(buffer, format="PNG")
    return buffer.getvalue()


def create_site(client: Client, *, code: str, name: str) -> dict:
    response = json_request(
        client,
        "post",
        "/api/v1/sites",
        {"name": name, "site_code": code, "latitude": "12.600000", "longitude": "15.200000"},
    )
    assert response.status_code == 201, response.content
    return response.json()


def create_assignment(client: Client, *, site_id: str, distributor_id: str, target: str) -> dict:
    response = json_request(
        client,
        "post",
        "/api/v1/assignments",
        {
            "site_id": site_id,
            "distributor_user_id": distributor_id,
            "target_quantity": target,
            "unit": "KG",
        },
    )
    assert response.status_code == 201, response.content
    return response.json()


def test_campaign_scope_and_internal_notes_are_not_exposed(org_factory):
    org = org_factory(campaign=True)
    unassigned = AuthClient()
    unassigned.create_distributor(email="unassigned@example.org", name="Unassigned")

    draft = json_request(
        org["admin_client"],
        "post",
        "/api/v1/campaigns",
        {
            "name": "Quiet campaign",
            "reference_code": "QUIET-9",
            "status": "DRAFT",
            "notes": "internal-only draft note",
        },
    )
    assert draft.status_code == 201, draft.content
    draft_id = draft.json()["id"]

    listed = unassigned.client.get("/api/v1/campaigns").json()["items"]
    assert all(row["id"] != draft_id for row in listed)
    assert unassigned.client.get(f"/api/v1/campaigns/{draft_id}").status_code == 404

    assigned = org["dist_client"].get(f"/api/v1/campaigns/{org['campaign_id']}")
    assert assigned.status_code == 200
    assert assigned.json()["notes"] is None
    admin_view = org["admin_client"].get(f"/api/v1/campaigns/{draft_id}")
    assert admin_view.json()["notes"] == "internal-only draft note"

    assignment_id = org["assignment"]["id"]
    note_update = json_request(
        org["admin_client"],
        "patch",
        f"/api/v1/assignments/{assignment_id}",
        {"notes": "internal assignment note"},
    )
    assert note_update.status_code == 200, note_update.content
    distributor_assignment = org["dist_client"].get(
        f"/api/v1/assignments/{assignment_id}"
    )
    assert distributor_assignment.json()["notes"] is None
    assert (
        org["admin_client"].get(f"/api/v1/assignments/{assignment_id}").json()["notes"]
        == "internal assignment note"
    )


def test_idempotency_keys_are_scoped_by_operation_and_payload(org_factory):
    org = org_factory()
    key = "shared-operation-key"
    receipt = json_request(
        org["admin_client"],
        "post",
        "/api/v1/inventory/receipts",
        {"quantity": "10", "unit": "KG", "source_reference": "scope-receipt"},
        HTTP_IDEMPOTENCY_KEY=key,
    )
    allocation = json_request(
        org["admin_client"],
        "post",
        "/api/v1/inventory/allocations",
        {
            "distributor_user_id": org["distributor_user_id"],
            "quantity": "5",
            "unit": "KG",
        },
        HTTP_IDEMPOTENCY_KEY=key,
    )
    assert receipt.status_code == 201, receipt.content
    assert allocation.status_code == 201, allocation.content
    assert receipt.json()["id"] != allocation.json()["id"]
    assert StockMovement.objects.filter(idempotency_key=key).count() == 2
    assert {row.idempotency_scope for row in StockMovement.objects.filter(idempotency_key=key)} == {
        "inventory.receipt",
        "inventory.allocation",
    }

    conflict = json_request(
        org["admin_client"],
        "post",
        "/api/v1/inventory/receipts",
        {"quantity": "99", "unit": "KG", "source_reference": "different-payload"},
        HTTP_IDEMPOTENCY_KEY=key,
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_legacy_idempotency_key_without_fingerprint_fails_closed(org_factory):
    org = org_factory()
    central = StockAccount.objects.get(account_type="CENTRAL")
    StockMovement.objects.create(
        movement_type="RECEIPT",
        destination_account=central,
        quantity_kg=Decimal("1"),
        reference_type="legacy_receipt",
        idempotency_scope="inventory.receipt",
        idempotency_key="legacy-replay-key",
        idempotency_fingerprint="",
    )
    response = json_request(
        org["admin_client"],
        "post",
        "/api/v1/inventory/receipts",
        {"quantity": "1", "unit": "KG", "source_reference": "retry-after-upgrade"},
        HTTP_IDEMPOTENCY_KEY="legacy-replay-key",
    )
    assert response.status_code == 409, response.content
    assert response.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert response.json()["error"]["details"][0]["legacy"] is True


def test_legacy_delivery_key_without_fingerprint_fails_closed(org_factory):
    org = org_factory()
    DistributionRecord.objects.create(
        campaign_id=org["campaign_id"],
        assignment_id=org["assignment"]["id"],
        site_id=org["site"]["id"],
        distributor_user_id=org["distributor_user_id"],
        quantity_kg=Decimal("5"),
        status="SUBMITTED",
        idempotency_key="legacy-delivery-key",
        idempotency_fingerprint="",
    )
    response = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="5",
        evidence=upload_png(org["dist_client"], color=(4, 5, 6)),
        idempotency_key="legacy-delivery-key",
    )
    assert response.status_code == 409, response.content
    assert response.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert response.json()["error"]["details"][0]["legacy"] is True


def test_approval_key_cannot_be_reused_for_another_already_approved_record(org_factory):
    org = org_factory()
    first = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="40",
        evidence=upload_png(org["dist_client"], color=(10, 20, 30)),
        idempotency_key="approval-key-first-submit",
    )
    second = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="30",
        evidence=upload_png(org["dist_client"], color=(30, 20, 10)),
        idempotency_key="approval-key-second-submit",
    )
    assert first.status_code == 201, first.content
    assert second.status_code == 201, second.content
    assert (
        approve(org["admin_client"], first.json()["id"], key="shared-approval-key").status_code
        == 200
    )
    assert (
        approve(org["admin_client"], second.json()["id"], key="second-approval-key").status_code
        == 200
    )

    replay = approve(org["admin_client"], second.json()["id"], key="shared-approval-key")
    assert replay.status_code == 409
    assert replay.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_adjustments_respect_pending_reservations(org_factory):
    org = org_factory()
    submitted = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="90",
        evidence=upload_png(org["dist_client"], color=(90, 80, 70)),
        idempotency_key="reservation-adjustment-submit",
    )
    assert submitted.status_code == 201, submitted.content
    distributor = distributor_account(org["admin_client"])
    central = central_account(org["admin_client"])
    assert distributor["available_kg"] == "10.000"

    loss = json_request(
        org["admin_client"],
        "post",
        "/api/v1/inventory/adjustments",
        {
            "account_id": distributor["id"],
            "quantity": "50",
            "unit": "KG",
            "movement_type": "LOSS",
            "reason": "Would consume stock reserved by a pending delivery.",
        },
        HTTP_IDEMPOTENCY_KEY="reservation-adjustment-loss",
    )
    assert loss.status_code == 409, loss.content
    assert loss.json()["error"]["code"] == "INSUFFICIENT_STOCK"
    assert loss.json()["error"]["details"][0]["available_kg"] == "10.000"

    returned = json_request(
        org["admin_client"],
        "post",
        "/api/v1/inventory/adjustments",
        {
            "account_id": distributor["id"],
            "destination_account_id": central["id"],
            "quantity": "50",
            "unit": "KG",
            "movement_type": "RETURN",
            "reason": "Would consume stock reserved by a pending delivery.",
        },
        HTTP_IDEMPOTENCY_KEY="reservation-adjustment-return",
    )
    assert returned.status_code == 409, returned.content
    assert returned.json()["error"]["code"] == "INSUFFICIENT_STOCK"


def test_reversal_of_receipt_reconciles_net_external_stock(org_factory):
    org = org_factory()
    receipt = json_request(
        org["admin_client"],
        "post",
        "/api/v1/inventory/receipts",
        {"quantity": "50", "unit": "KG", "source_reference": "reversible-load"},
        HTTP_IDEMPOTENCY_KEY="reverse-receipt",
    )
    assert receipt.status_code == 201, receipt.content

    reversal = json_request(
        org["admin_client"],
        "post",
        f"/api/v1/inventory/movements/{receipt.json()['id']}/reversal",
        {"reason": "weighed incorrectly at intake"},
        HTTP_IDEMPOTENCY_KEY="reverse-receipt-correction",
    )
    assert reversal.status_code == 201, reversal.content

    reconciliation = org["admin_client"].get("/api/v1/inventory/summary").json()["reconciliation"]
    assert Decimal(reconciliation["received_kg"]) == Decimal("550.000")
    assert Decimal(reconciliation["reversed_receipt_kg"]) == Decimal("50.000")
    assert Decimal(reconciliation["net_external_kg"]) == Decimal("500.000")
    assert Decimal(reconciliation["sum_account_balances_kg"]) == Decimal("500.000")
    assert reconciliation["balanced"] is True


def test_loss_reversal_reconciles_and_reversal_of_reversal_is_refused(org_factory):
    org = org_factory()
    central = central_account(org["admin_client"])
    loss = json_request(
        org["admin_client"],
        "post",
        "/api/v1/inventory/adjustments",
        {
            "account_id": central["id"],
            "quantity": "30",
            "unit": "KG",
            "movement_type": "LOSS",
            "reason": "Synthetic rodent damage.",
        },
        HTTP_IDEMPOTENCY_KEY="reverse-loss",
    )
    assert loss.status_code == 201, loss.content

    reversal = json_request(
        org["admin_client"],
        "post",
        f"/api/v1/inventory/movements/{loss.json()['id']}/reversal",
        {"reason": "Loss was recorded against the wrong bag lot."},
        HTTP_IDEMPOTENCY_KEY="reverse-loss-correction",
    )
    assert reversal.status_code == 201, reversal.content

    nested = json_request(
        org["admin_client"],
        "post",
        f"/api/v1/inventory/movements/{reversal.json()['id']}/reversal",
        {"reason": "Attempt to reverse a compensating movement."},
        HTTP_IDEMPOTENCY_KEY="reverse-loss-nested",
    )
    assert nested.status_code == 409, nested.content
    assert nested.json()["error"]["code"] == "ILLEGAL_STATE"

    reconciliation = org["admin_client"].get("/api/v1/inventory/summary").json()["reconciliation"]
    assert Decimal(reconciliation["loss_kg"]) == Decimal("30.000")
    assert Decimal(reconciliation["reversed_loss_kg"]) == Decimal("30.000")
    assert Decimal(reconciliation["net_external_kg"]) == Decimal("500.000")
    assert Decimal(reconciliation["sum_account_balances_kg"]) == Decimal("500.000")
    assert reconciliation["balanced"] is True


def test_reversal_cannot_overdraw_a_distributor_after_delivery(org_factory):
    org = org_factory()
    evidence = upload_png(org["dist_client"])
    submitted = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="80",
        evidence=evidence,
        idempotency_key="reverse-overdraw-submit",
    )
    assert submitted.status_code == 201, submitted.content
    approved = approve(
        org["admin_client"], submitted.json()["id"], key="reverse-overdraw-approve"
    )
    assert approved.status_code == 200, approved.content

    allocation = StockMovement.objects.get(
        movement_type="TRANSFER", reference_type="admin_allocation"
    )
    blocked = json_request(
        org["admin_client"],
        "post",
        f"/api/v1/inventory/movements/{allocation.id}/reversal",
        {"reason": "attempted allocation rollback"},
        HTTP_IDEMPOTENCY_KEY="reverse-overdraw",
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "INSUFFICIENT_STOCK"
    assert StockMovement.objects.filter(reversal_of=allocation).count() == 0


def test_reversing_delivery_updates_record_and_analytics(org_factory):
    org = org_factory()
    evidence = upload_png(org["dist_client"])
    submitted = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="50",
        evidence=evidence,
        idempotency_key="reverse-delivery-submit",
    )
    approved = approve(
        org["admin_client"], submitted.json()["id"], key="reverse-delivery-approve"
    )
    assert approved.status_code == 200, approved.content
    record_id = submitted.json()["id"]
    movement_id = approved.json()["stock_movement_id"]
    assert movement_id

    reversal = json_request(
        org["admin_client"],
        "post",
        f"/api/v1/inventory/movements/{movement_id}/reversal",
        {"reason": "delivery confirmed at wrong site"},
        HTTP_IDEMPOTENCY_KEY="reverse-delivery",
    )
    assert reversal.status_code == 201, reversal.content

    record = DistributionRecord.objects.get(id=record_id)
    assert record.status == "REVERSED"
    assert record.reversed_at is not None
    assert str(record.reversed_by_id) == org["admin_user"]["id"]
    assert record.reversal_reason == "delivery confirmed at wrong site"
    assert record.stock_movement_id is not None  # history is preserved

    distributor = distributor_account(org["admin_client"])
    ledger = org["admin_client"].get(
        f"/api/v1/inventory/accounts/{distributor['id']}/ledger?limit=50"
    ).json()["items"]
    original_row = next(row for row in ledger if row["id"] == movement_id)
    assert original_row["reversed_by_id"] == reversal.json()["id"]

    overview = org["dist_client"].get("/api/v1/analytics/overview").json()
    assert Decimal(overview["approved_delivered_kg"]) == Decimal("0.000")
    assert Decimal(overview["target_kg"]) == Decimal("150.000")
    assert Decimal(overview["remaining_target_kg"]) == Decimal("150.000")
    summary = org["admin_client"].get("/api/v1/inventory/summary").json()
    assert summary["reconciliation"]["balanced"] is True


def test_unvisited_assignment_target_is_not_dropped(org_factory):
    org = org_factory()
    overview = org["admin_client"].get("/api/v1/analytics/overview").json()
    assert Decimal(overview["target_kg"]) == Decimal("150.000")
    assert Decimal(overview["remaining_target_kg"]) == Decimal("150.000")

    distributor_overview = org["dist_client"].get("/api/v1/analytics/overview").json()
    assert Decimal(distributor_overview["target_kg"]) == Decimal("150.000")


def test_target_math_uses_all_assignments_and_all_time_approvals(org_factory):
    org = org_factory()
    submitted = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="50",
        evidence=upload_png(org["dist_client"]),
        idempotency_key="target-math-submit",
    )
    assert submitted.status_code == 201, submitted.content
    assert (
        approve(org["admin_client"], submitted.json()["id"], key="target-math-approve").status_code
        == 200
    )

    overview = org["admin_client"].get(
        "/api/v1/analytics/overview?from=2099-01-01T00:00:00Z"
    ).json()
    assert Decimal(overview["approved_delivered_kg"]) == Decimal("0.000")
    assert Decimal(overview["target_kg"]) == Decimal("150.000")
    assert Decimal(overview["remaining_target_kg"]) == Decimal("100.000")


def test_distributor_site_stock_is_scoped_to_own_assignments(org_factory, auth: AuthClient):
    org = org_factory()
    other = auth.create_distributor(email="second@example.org", name="Second Distributor")
    other_site = create_site(org["admin_client"], code="SD-02", name="South Depot")
    other_assignment = create_assignment(
        org["admin_client"],
        site_id=other_site["id"],
        distributor_id=other["id"],
        target="50",
    )
    second_alloc = json_request(
        org["admin_client"],
        "post",
        "/api/v1/inventory/allocations",
        {"distributor_user_id": other["id"], "quantity": "100", "unit": "KG"},
        HTTP_IDEMPOTENCY_KEY="second-alloc",
    )
    assert second_alloc.status_code == 201, second_alloc.content

    first_evidence = upload_png(org["dist_client"], color=(1, 10, 100))
    first_submit = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="40",
        evidence=first_evidence,
        idempotency_key="scope-first",
    )
    assert approve(org["admin_client"], first_submit.json()["id"], key="scope-first-approve").status_code == 200

    other_client = AuthClient()
    other_client.login("second@example.org", DISTRIBUTOR_PASSWORD)
    second_evidence = upload_png(other_client.client, color=(2, 20, 200))
    second_submit = submit_delivery(
        other_client.client,
        assignment_id=other_assignment["id"],
        quantity="30",
        evidence=second_evidence,
        idempotency_key="scope-second",
    )
    assert second_submit.status_code == 201, second_submit.content
    assert approve(
        org["admin_client"], second_submit.json()["id"], key="scope-second-approve"
    ).status_code == 200

    overview = org["dist_client"].get("/api/v1/analytics/overview").json()
    assert Decimal(overview["stock"]["site_stock_kg"]) == Decimal("40.000")


@pytest.mark.django_db(transaction=True)
def test_concurrent_first_site_account_creation_is_idempotent(org_factory):
    org = org_factory()
    site_id = org["site"]["id"]
    assert not StockAccount.objects.filter(account_type="SITE", site_id=site_id).exists()
    barrier = threading.Barrier(6)
    errors: list[BaseException] = []

    def create() -> None:
        try:
            barrier.wait(timeout=5)
            with transaction.atomic():
                get_or_create_site_account(site_id)
        except BaseException as exc:  # noqa: BLE001 - collected for the assertion
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=create) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert StockAccount.objects.filter(account_type="SITE", site_id=site_id).count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_approvals_cannot_exceed_assignment_target(org_factory):
    org = org_factory()
    extra = json_request(
        org["admin_client"],
        "post",
        "/api/v1/inventory/allocations",
        {"distributor_user_id": org["distributor_user_id"], "quantity": "100", "unit": "KG"},
        HTTP_IDEMPOTENCY_KEY="race-extra-alloc",
    )
    assert extra.status_code == 201, extra.content
    target = json_request(
        org["admin_client"],
        "patch",
        f"/api/v1/assignments/{org['assignment']['id']}",
        {"target_quantity": "100", "unit": "KG"},
    )
    assert target.status_code == 200, target.content

    records = []
    for index, color in ((1, (3, 30, 10)), (2, (4, 40, 20))):
        evidence = upload_png(org["dist_client"], color=color)
        response = submit_delivery(
            org["dist_client"],
            assignment_id=org["assignment"]["id"],
            quantity="60",
            evidence=evidence,
            idempotency_key=f"target-race-submit-{index}",
        )
        assert response.status_code == 201, response.content
        records.append(response.json()["id"])

    admin_one = AuthClient()
    admin_one.login("admin@example.org", "Sup3rAdminPass!")
    admin_two = AuthClient()
    admin_two.login("admin@example.org", "Sup3rAdminPass!")
    results: dict[int, tuple[int, str]] = {}

    def run(index: int, client: Client, record_id: str) -> None:
        try:
            response = approve(client, record_id, key=f"target-race-approve-{index}")
            results[index] = (response.status_code, response.content.decode())
        finally:
            connection.close()

    threads = [
        threading.Thread(target=run, args=(1, admin_one.client, records[0])),
        threading.Thread(target=run, args=(2, admin_two.client, records[1])),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(code for code, _ in results.values()) == [200, 409], results
    assert DistributionRecord.objects.filter(status="APPROVED").count() == 1
    delivered = StockMovement.objects.filter(movement_type="DELIVERY").aggregate(
        total=Sum("quantity_kg")
    )["total"]
    assert Decimal(delivered or 0) == Decimal("60.000")


def test_direct_object_storage_upload_can_be_completed_and_attached(org_factory):
    org = org_factory()
    intent_response = json_request(
        org["dist_client"],
        "post",
        "/api/v1/evidence/upload-intents",
        {"content_type": "image/png"},
    )
    assert intent_response.status_code == 201, intent_response.content
    intent_id = intent_response.json()["intent_id"]
    intent = UploadIntent.objects.get(id=intent_id)

    # Simulate a browser that PUT the object directly to S3/MinIO: Django never
    # sees the bytes, so received_sha256_hex is still null.
    data = png_bytes((9, 99, 9))
    get_storage_service().put_object(intent.storage_key, data, "image/png")
    intent.refresh_from_db()
    assert intent.received_sha256_hex is None

    completed = json_request(
        org["dist_client"], "post", f"/api/v1/evidence/upload-intents/{intent_id}/complete"
    )
    assert completed.status_code == 200, completed.content
    assert completed.json()["newly_verified"] is True
    assert completed.json()["size_bytes"] == len(data)
    assert len(completed.json()["sha256_hex"]) == 64

    submitted = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="25",
        evidence={"intent_id": intent_id, "capture_source": "CAMERA"},
        idempotency_key="direct-upload-submit",
    )
    assert submitted.status_code == 201, submitted.content


@override_settings(
    STORAGE_ENDPOINT_URL="http://minio.invalid:9000",
    STORAGE_REGION="us-east-1",
    STORAGE_BUCKET="synthetic-evidence",
    STORAGE_ACCESS_KEY_ID="synthetic-access",
    STORAGE_SECRET_ACCESS_KEY="synthetic-secret",
    STORAGE_SERVER_SIDE_ENCRYPTION="AES256",
    STORAGE_KMS_KEY_ID="",
)
def test_s3_upload_instructions_include_encryption_header():
    service = S3StorageService()
    headers = service.upload_headers("image/png")
    assert headers == {
        "Content-Type": "image/png",
        "x-amz-server-side-encryption": "AES256",
    }
    service.client = MagicMock()
    service.client.generate_presigned_url.return_value = "https://objects.invalid/put"
    url = service.presigned_put("evidence/opaque-key", "image/png", 1024, expires_in=60)
    assert url == "https://objects.invalid/put"
    _, kwargs = service.client.generate_presigned_url.call_args
    assert kwargs["Params"]["ServerSideEncryption"] == "AES256"
    assert kwargs["ExpiresIn"] == 60


@override_settings(
    STORAGE_ENDPOINT_URL="https://t3.storageapi.dev",
    STORAGE_REGION="auto",
    STORAGE_BUCKET="demo-bucket",
    STORAGE_ACCESS_KEY_ID="synthetic-access",
    STORAGE_SECRET_ACCESS_KEY="synthetic-secret",
    STORAGE_SERVER_SIDE_ENCRYPTION="",
    STORAGE_KMS_KEY_ID="",
    STORAGE_ADDRESSING_STYLE="virtual",
)
def test_s3_virtual_host_addressing_is_configurable():
    service = S3StorageService()
    url = service.presigned_put("evidence/opaque-key", "image/png", 1024, expires_in=60)
    assert url.split("?")[0] == "https://demo-bucket.t3.storageapi.dev/evidence/opaque-key"


@override_settings(
    STORAGE_ENDPOINT_URL="http://minio.invalid:9000",
    STORAGE_REGION="us-east-1",
    STORAGE_BUCKET="synthetic-evidence",
    STORAGE_ACCESS_KEY_ID="synthetic-access",
    STORAGE_SECRET_ACCESS_KEY="synthetic-secret",
    STORAGE_SERVER_SIDE_ENCRYPTION="AES256",
    STORAGE_KMS_KEY_ID="",
)
def test_s3_health_converts_endpoint_errors_to_unreachable():
    from botocore.exceptions import EndpointConnectionError

    service = S3StorageService()
    service.client = MagicMock()
    service.client.head_bucket.side_effect = EndpointConnectionError(
        endpoint_url="http://minio.invalid:9000"
    )
    assert service.health() == {"mode": "s3", "configured": True, "reachable": False}


def test_failed_evidence_attachment_rolls_back_submission(org_factory):
    org = org_factory()
    intent_response = json_request(
        org["dist_client"],
        "post",
        "/api/v1/evidence/upload-intents",
        {"content_type": "image/png"},
    )
    intent_id = intent_response.json()["intent_id"]

    failed = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="25",
        evidence={"intent_id": intent_id, "capture_source": "CAMERA"},
        idempotency_key="atomic-evidence-submit",
    )
    assert failed.status_code == 400
    assert not DistributionRecord.objects.filter(
        distributor_user_id=org["distributor_user_id"],
        idempotency_key="atomic-evidence-submit",
    ).exists()

    intent = UploadIntent.objects.get(id=intent_id)
    get_storage_service().put_object(intent.storage_key, png_bytes((8, 9, 10)), "image/png")
    retry = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="25",
        evidence={"intent_id": intent_id, "capture_source": "CAMERA"},
        idempotency_key="atomic-evidence-submit",
    )
    assert retry.status_code == 201, retry.content
    assert PhotoEvidence.objects.filter(distribution_record_id=retry.json()["id"]).count() == 1


def test_evidence_object_changed_after_completion_is_rejected(org_factory):
    org = org_factory()
    intent_response = json_request(
        org["dist_client"],
        "post",
        "/api/v1/evidence/upload-intents",
        {"content_type": "image/png"},
    )
    intent_id = intent_response.json()["intent_id"]
    intent = UploadIntent.objects.get(id=intent_id)
    get_storage_service().put_object(intent.storage_key, png_bytes((1, 2, 3)), "image/png")
    completed = json_request(
        org["dist_client"], "post", f"/api/v1/evidence/upload-intents/{intent_id}/complete"
    )
    assert completed.status_code == 200

    get_storage_service().put_object(intent.storage_key, png_bytes((3, 2, 1)), "image/png")
    response = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="25",
        evidence={"intent_id": intent_id, "capture_source": "CAMERA"},
        idempotency_key="tampered-upload-submit",
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EVIDENCE_INTEGRITY_FAILURE"


def test_storage_reads_are_bounded_before_decode(org_factory):
    org = org_factory()
    intent_response = json_request(
        org["dist_client"],
        "post",
        "/api/v1/evidence/upload-intents",
        {"content_type": "image/png"},
    )
    intent_id = intent_response.json()["intent_id"]
    intent = UploadIntent.objects.get(id=intent_id)
    get_storage_service().put_object(intent.storage_key, png_bytes((5, 6, 7)), "image/png")
    completed = json_request(
        org["dist_client"], "post", f"/api/v1/evidence/upload-intents/{intent_id}/complete"
    )
    assert completed.status_code == 200, completed.content

    oversized = b"x" * (settings.MAX_EVIDENCE_UPLOAD_BYTES + 1)
    get_storage_service().put_object(intent.storage_key, oversized, "image/png")
    response = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="25",
        evidence={"intent_id": intent_id, "capture_source": "CAMERA"},
        idempotency_key="oversized-replacement-submit",
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert not DistributionRecord.objects.filter(
        idempotency_key="oversized-replacement-submit"
    ).exists()


def test_same_size_evidence_replacement_is_rejected_on_read(org_factory):
    org = org_factory()
    submitted = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="7",
        evidence=upload_png(org["dist_client"], color=(7, 7, 7)),
        idempotency_key="same-size-replacement-submit",
    )
    assert submitted.status_code == 201, submitted.content
    evidence = PhotoEvidence.objects.get(distribution_record_id=submitted.json()["id"])
    original = get_storage_service().get_object(evidence.storage_key)
    get_storage_service().put_object(
        evidence.storage_key, b"x" * len(original), evidence.content_type
    )
    view_url = org["admin_client"].get(f"/api/v1/evidence/{evidence.id}/view-url")
    assert view_url.status_code == 200, view_url.content
    blob = org["admin_client"].get(view_url.json()["url"])
    assert blob.status_code == 409, blob.content
    assert blob.json()["error"]["code"] == "EVIDENCE_INTEGRITY_FAILURE"


def test_forwarded_for_is_ignored_without_trusted_proxy_opt_in():
    request = RequestFactory().get(
        "/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="203.0.113.9"
    )
    with override_settings(TRUST_X_FORWARDED_FOR=False):
        assert client_ip(request) == "127.0.0.1"
    with override_settings(TRUST_X_FORWARDED_FOR=True):
        assert client_ip(request) == "203.0.113.9"


def test_rate_limit_store_is_bounded(monkeypatch):
    from corn import rate_limit

    monkeypatch.setattr(rate_limit, "MAX_BUCKETS", 3)
    rate_limit.reset_for_tests()
    for index in range(5):
        allowed, _ = rate_limit.hit("deliveries.create", f"203.0.113.{index}")
        assert allowed
    assert list(rate_limit._events) == [
        "deliveries.create:203.0.113.2",
        "deliveries.create:203.0.113.3",
        "deliveries.create:203.0.113.4",
    ]


def test_readiness_reports_storage_failure(monkeypatch):
    monkeypatch.setattr(
        "corn.views.health.storage_health_probe",
        lambda: {"mode": "s3", "configured": True, "reachable": False},
    )
    response = Client().get("/health/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["storage"] == "unavailable"


def test_security_headers_include_cross_origin_isolation():
    response = Client().get("/health/live")
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "microphone=()" in response.headers["Permissions-Policy"]


def test_referer_is_checked_when_origin_is_absent_on_unsafe_requests():
    response = json_request(
        Client(),
        "post",
        "/api/v1/auth/login",
        {"email": "nobody@example.org", "password": "synthetic-wrong-password"},
        HTTP_REFERER="https://evil.example/phish",
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_oversized_idempotency_key_is_rejected_at_the_boundary(org_factory):
    org = org_factory()
    response = json_request(
        org["admin_client"],
        "post",
        "/api/v1/inventory/receipts",
        {"quantity": "1", "unit": "KG", "source_reference": "too-long-key"},
        HTTP_IDEMPOTENCY_KEY="k" * 129,
    )
    assert response.status_code == 400
    assert response.json()["error"]["details"][0]["field"] == "Idempotency-Key"
