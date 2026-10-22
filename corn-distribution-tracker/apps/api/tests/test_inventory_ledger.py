"""Ledger integrity, concurrency, conversion and idempotency tests."""

from __future__ import annotations

import threading
from decimal import Decimal

import pytest
from django.db import DatabaseError, connection, transaction
from django.test import Client

from corn.models import StockMovement
from corn.services import inventory as inventory_service
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
    return next(account for account in summary["accounts"] if account["account_type"] == "CENTRAL")


def distributor_account(client: Client) -> dict:
    summary = client.get("/api/v1/inventory/summary").json()
    return next(account for account in summary["accounts"] if account["account_type"] == "DISTRIBUTOR")


def test_receipt_is_idempotent_under_retry(org_factory):
    org = org_factory()
    payload = {
        "quantity": "250.5",
        "unit": "KG",
        "source_reference": "load-7",
        "received_at": "2026-10-20T08:00:00Z",
        "notes": "morning load",
    }
    first = json_request(
        org["admin_client"],
        "post",
        "/api/v1/inventory/receipts",
        payload,
        HTTP_IDEMPOTENCY_KEY="receipt-load-7",
    )
    retry = json_request(
        org["admin_client"],
        "post",
        "/api/v1/inventory/receipts",
        payload,
        HTTP_IDEMPOTENCY_KEY="receipt-load-7",
    )
    assert first.status_code == 201 and retry.status_code == 201
    assert first.json()["id"] == retry.json()["id"]
    assert StockMovement.objects.filter(idempotency_key="receipt-load-7").count() == 1
    assert first.json()["quantity_kg"] == "250.500"


def test_allocation_requires_sufficient_central_stock(org_factory):
    org = org_factory()
    response = json_request(
        org["admin_client"],
        "post",
        "/api/v1/inventory/allocations",
        {"distributor_user_id": org["distributor_user_id"], "quantity": "100000", "unit": "KG"},
        HTTP_IDEMPOTENCY_KEY="alloc-huge",
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INSUFFICIENT_STOCK"


def test_approve_posts_exactly_one_movement_and_is_idempotent(org_factory):
    org = org_factory()
    evidence = upload_png(org["dist_client"])
    submitted = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="40",
        evidence=evidence,
        idempotency_key="sub-1",
    )
    assert submitted.status_code == 201, submitted.content
    record_id = submitted.json()["id"]

    first = json_request(
        org["admin_client"],
        "post",
        f"/api/v1/deliveries/{record_id}/approve",
        {},
        HTTP_IDEMPOTENCY_KEY="appr-1",
    )
    assert first.status_code == 200, first.content
    second = json_request(
        org["admin_client"],
        "post",
        f"/api/v1/deliveries/{record_id}/approve",
        {},
        HTTP_IDEMPOTENCY_KEY="appr-2",
    )
    assert second.status_code == 200
    assert second.json()["status"] == "APPROVED"
    deliveries = StockMovement.objects.filter(movement_type="DELIVERY")
    assert deliveries.count() == 1
    assert str(deliveries.get().quantity_kg) == "40.000"


def test_reject_releases_reservation_without_stock_change(org_factory):
    org = org_factory()
    evidence = upload_png(org["dist_client"])
    submitted = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="25",
        evidence=evidence,
        idempotency_key="sub-rej",
        include_location=False,
    )
    assert submitted.status_code == 201, submitted.content
    record_id = submitted.json()["id"]
    before = distributor_account(org["admin_client"])

    anonymous = json_request(
        Client(), "post", f"/api/v1/deliveries/{record_id}/reject", {"reason": "Quantity mismatch."}
    )
    assert anonymous.status_code == 401
    between = distributor_account(org["admin_client"])
    assert between["reserved_kg"] == before["reserved_kg"]

    rejected = json_request(
        org["admin_client"],
        "post",
        f"/api/v1/deliveries/{record_id}/reject",
        {"reason": "Quantity mismatch in the field."},
    )
    assert rejected.status_code == 200, rejected.content
    assert rejected.json()["status"] == "REJECTED"
    after = distributor_account(org["admin_client"])
    assert after["posted_balance_kg"] == before["posted_balance_kg"]
    assert after["reserved_kg"] == "0.000"


def test_adjustment_requires_reason_and_blocks_negative(org_factory):
    org = org_factory()
    central = central_account(org["admin_client"])
    no_reason = json_request(
        org["admin_client"],
        "post",
        "/api/v1/inventory/adjustments",
        {
            "account_id": central["id"],
            "quantity": "10",
            "unit": "KG",
            "movement_type": "LOSS",
            "reason": "  ",
        },
    )
    assert no_reason.status_code == 422
    too_much = json_request(
        org["admin_client"],
        "post",
        "/api/v1/inventory/adjustments",
        {
            "account_id": central["id"],
            "quantity": "100000",
            "unit": "KG",
            "movement_type": "LOSS",
            "reason": "rodent damage",
        },
    )
    assert too_much.status_code == 409
    assert too_much.json()["error"]["code"] == "INSUFFICIENT_STOCK"


def test_adjustment_return_requires_real_destination(org_factory):
    org = org_factory()
    central = central_account(org["admin_client"])
    missing = json_request(
        org["admin_client"],
        "post",
        "/api/v1/inventory/adjustments",
        {
            "account_id": central["id"],
            "quantity": "10",
            "unit": "KG",
            "movement_type": "RETURN",
            "reason": "return to warehouse",
            "destination_account_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert missing.status_code == 404


@pytest.mark.django_db(transaction=True)
def test_approve_serializes_concurrent_reviews(org_factory):
    """Two approvals against the same submitted record post one movement only."""
    org = org_factory()
    evidence = upload_png(org["dist_client"])
    submitted = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="45",
        evidence=evidence,
        idempotency_key="sub-approve-race",
    )
    assert submitted.status_code == 201, submitted.content
    record_id = submitted.json()["id"]
    admin = AuthClient()
    admin.login("admin@example.org", "Sup3rAdminPass!")
    other = AuthClient()
    other.login("admin@example.org", "Sup3rAdminPass!")
    results: dict[int, int] = {}

    def approve(index: int, client: Client) -> None:
        try:
            response = json_request(
                client,
                "post",
                f"/api/v1/deliveries/{record_id}/approve",
                {},
                HTTP_IDEMPOTENCY_KEY=f"race-approve-{index}",
            )
            results[index] = response.status_code
        finally:
            connection.close()

    threads = [
        threading.Thread(target=approve, args=(1, admin.client)),
        threading.Thread(target=approve, args=(2, other.client)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results.values()) == [200, 200]
    assert StockMovement.objects.filter(movement_type="DELIVERY").count() == 1


def test_reversal_is_compensating_and_append_only(org_factory):
    org = org_factory()
    ledger = org["admin_client"].get(
        f"/api/v1/inventory/accounts/{central_account(org['admin_client'])['id']}/ledger"
    ).json()
    movement_id = ledger["items"][0]["id"]
    reversal = json_request(
        org["admin_client"],
        "post",
        f"/api/v1/inventory/movements/{movement_id}/reversal",
        {"reason": "entry recorded against wrong lot"},
    )
    assert reversal.status_code == 201, reversal.content
    assert StockMovement.objects.filter(reversal_of_id=movement_id).count() == 1

    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE stock_movements SET quantity_kg = 1 WHERE id = %s", [movement_id]
                )


@pytest.mark.django_db(transaction=True)
def test_append_only_triggers_reject_delete(org_factory):
    org_factory()
    movement = StockMovement.objects.first()
    assert movement is not None
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM stock_movements WHERE id = %s", [movement.id])


def test_reconciliation_balances(org_factory):
    org = org_factory()
    summary = org["admin_client"].get("/api/v1/inventory/summary").json()
    reconciliation = summary["reconciliation"]
    assert reconciliation is not None
    assert reconciliation["balanced"] is True
    assert Decimal(reconciliation["sum_account_balances_kg"]) == Decimal("500.000")


def test_unit_conversions_quintal_tonne_bag(org_factory):
    org = org_factory()
    settings_response = json_request(
        org["admin_client"], "patch", "/api/v1/settings", {"kg_per_bag": "50"}
    )
    assert settings_response.status_code == 200, settings_response.content
    for unit, quantity, expected in (
        ("QUINTAL", "2", "200.000"),
        ("TONNE", "0.5", "500.000"),
        ("BAG", "10", "500.000"),
    ):
        response = json_request(
            org["admin_client"],
            "post",
            "/api/v1/inventory/receipts",
            {"quantity": quantity, "unit": unit, "source_reference": f"unit-test-{unit}"},
            HTTP_IDEMPOTENCY_KEY=f"unit-test-{unit}",
        )
        assert response.status_code == 201, (unit, response.content)
        assert response.json()["quantity_kg"] == expected

    display = org["admin_client"].get(
        "/api/v1/inventory/display-unit?quantity_kg=500&unit=BAG"
    )
    assert display.status_code == 200
    assert display.json()["factor_label"] == "1 bag = 50 kg"
    assert display.json()["display_value"] == "10.00"

    over_precise = json_request(
        org["admin_client"],
        "post",
        "/api/v1/inventory/receipts",
        {"quantity": "12.34567", "unit": "KG", "source_reference": "precise"},
    )
    assert over_precise.status_code == 422


@pytest.mark.django_db(transaction=True)
def test_concurrent_submissions_cannot_overspend_stock(org_factory):
    """Two simultaneous 80 kg submissions against 100 kg: one wins, one is refused."""
    org = org_factory()
    evidence_one = upload_png(org["dist_client"], color=(1, 2, 3))
    evidence_two = upload_png(org["dist_client"], color=(4, 5, 6))
    first = AuthClient()
    first.login("dist1@example.org", DISTRIBUTOR_PASSWORD)
    second = AuthClient()
    second.login("dist1@example.org", DISTRIBUTOR_PASSWORD)
    results: dict[int, tuple[int, str]] = {}

    def submit(index: int, client: Client, evidence: dict) -> None:
        try:
            response = submit_delivery(
                client,
                assignment_id=org["assignment"]["id"],
                quantity="80",
                evidence=evidence,
                idempotency_key=f"race-{index}",
            )
            results[index] = (response.status_code, response.content.decode())
        finally:
            connection.close()

    threads = [
        threading.Thread(target=submit, args=(1, first.client, evidence_one)),
        threading.Thread(target=submit, args=(2, second.client, evidence_two)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(status for status, _ in results.values()) == [201, 409], results
    reserved = inventory_service.reserved_kg(org["distributor_user_id"])
    assert reserved <= Decimal("100.000")
