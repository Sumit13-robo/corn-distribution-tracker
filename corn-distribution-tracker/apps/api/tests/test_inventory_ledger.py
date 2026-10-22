"""Ledger integrity, concurrency, conversion and idempotency tests."""

from __future__ import annotations

import threading

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.models import StockMovement
from tests.conftest import _make_session


def _balance(db, account_id) -> float:
    inflow = db.execute(
        text("SELECT COALESCE(SUM(quantity_kg), 0) FROM stock_movements WHERE destination_account_id = :a"),
        {"a": str(account_id)},
    ).scalar()
    outflow = db.execute(
        text("SELECT COALESCE(SUM(quantity_kg), 0) FROM stock_movements WHERE source_account_id = :a"),
        {"a": str(account_id)},
    ).scalar()
    return float(inflow) - float(outflow)


def _central_balance(db) -> float:
    return db.execute(
        text(
            "SELECT COALESCE(SUM(quantity_kg),0) FROM stock_movements WHERE destination_account_id IS NOT NULL "
            "AND movement_type='RECEIPT'"
        )
    ).scalar_one()


def test_receipt_is_idempotent_under_retry(org_factory, client: TestClient):
    org = org_factory()
    payload = {
        "quantity": "250.5",
        "unit": "KG",
        "source_reference": "load-7",
        "received_at": "2026-10-20T08:00:00Z",
        "notes": "morning load",
    }
    headers = {**org["headers_admin"], "Idempotency-Key": "receipt-load-7"}
    first = client.post("/api/v1/inventory/receipts", json=payload, headers=headers)
    assert first.status_code == 201
    retry = client.post("/api/v1/inventory/receipts", json=payload, headers=headers)
    assert retry.status_code == 201
    assert first.json()["id"] == retry.json()["id"], "idempotent retry must return the original movement"

    db = _make_session()
    try:
        # The org seed also posts a receipt (key "test-receipt-1"), so scope the
        # count to this test's idempotency key.
        receipts = list(
            db.scalars(select(StockMovement).where(StockMovement.idempotency_key == "receipt-load-7"))
        )
        assert len(receipts) == 1, "duplicate idempotency keys must not duplicate movement rows"
        assert str(receipts[0].quantity_kg) == "250.500"
    finally:
        db.close()


def test_allocation_requires_sufficient_central_stock(org_factory, client: TestClient):
    org = org_factory()  # 500 received, 100 allocated
    resp = client.post(
        "/api/v1/inventory/allocations",
        json={"distributor_user_id": org["distributor_user_id"], "quantity": "100000", "unit": "KG"},
        headers={**org["headers_admin"], "Idempotency-Key": "alloc-huge"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "INSUFFICIENT_STOCK"


def test_concurrent_submissions_cannot_overspend_stock(org_factory, client: TestClient):
    """Two simultaneous distributor submissions at the availability boundary.

    The distributor has 100 kg; two 80 kg submissions race: exactly one records,
    the other returns INSUFFICIENT_STOCK, and reserved never exceeds the posting.
    """
    org = org_factory()

    def make_intent_and_upload(content_type="image/jpeg"):
        intent = client.post(
            "/api/v1/evidence/upload-intents",
            json={"content_type": content_type},
            headers=org["headers_dist"],
        ).json()
        from io import BytesIO

        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (4, 4), (100, 130, 70)).save(buf, format="JPEG")
        data = buf.getvalue()
        put = client.put(intent["upload_url"], content=data, headers=org["headers_dist"])
        assert put.status_code == 204, put.text
        return {
            "intent_id": intent["intent_id"],
            "capture_source": "CAMERA",
            "client_captured_at": "2026-10-21T10:00:00Z",
        }

    evidence = make_intent_and_upload()
    base = {
        "assignment_id": org["assignment"]["id"],
        "quantity": "80",
        "unit": "KG",
        "evidence": [evidence],
        "location": {
            "latitude": "12.551900",
            "longitude": "15.000100",
            "accuracy_m": "8",
            "timestamp": "2026-10-21T10:00:00Z",
        },
    }

    results: dict[int, Response] = {}

    def submit(idx: int, key: str) -> None:
        response = client.post(
            "/api/v1/deliveries",
            json=base,
            headers={**org["headers_dist"], "Idempotency-Key": key},
        )
        results[idx] = response

    threads = [threading.Thread(target=submit, args=(i, f"race-{i}")) for i in range(1, 3)]
    threads[0].start()
    threads[1].start()
    threads[0].join()
    threads[1].join()

    statuses = sorted(r.status_code for r in results.values())
    assert statuses == [201, 409], f"{statuses}: {[getattr(r, 'text', r) for r in (results[1], results[2])]}"
    db = _make_session()
    try:
        reserved = db.execute(
            text("SELECT COALESCE(SUM(quantity_kg),0) FROM distribution_records WHERE status='SUBMITTED'")
        ).scalar()
        assert reserved <= 100  # posted balance of the distributor account
    finally:
        db.close()


def test_approve_posts_exactly_one_movement_and_is_idempotent(org_factory, client: TestClient):
    org = org_factory()
    # Submit a delivery of 40 kg
    from io import BytesIO

    from PIL import Image

    intent = client.post(
        "/api/v1/evidence/upload-intents", json={"content_type": "image/jpeg"}, headers=org["headers_dist"]
    ).json()
    buf = BytesIO()
    Image.new("RGB", (4, 4), (150, 120, 40)).save(buf, format="JPEG")
    client.put(intent["upload_url"], content=buf.getvalue(), headers=org["headers_dist"])
    submit = client.post(
        "/api/v1/deliveries",
        json={
            "assignment_id": org["assignment"]["id"],
            "quantity": "40",
            "unit": "KG",
            "evidence": [{"intent_id": intent["intent_id"], "capture_source": "CAMERA"}],
            "location": {
                "latitude": "12.552",
                "longitude": "15.1004",
                "accuracy_m": "5",
                "timestamp": "2026-10-21T09:30:00Z",
            },
        },
        headers={**org["headers_dist"], "Idempotency-Key": "sub-1"},
    )
    assert submit.status_code == 201, submit.text
    record_id = submit.json()["id"]

    first = client.post(
        f"/api/v1/deliveries/{record_id}/approve",
        json={},
        headers={**org["headers_admin"], "Idempotency-Key": "appr-1"},
    )
    assert first.status_code == 200, first.text
    second = client.post(
        f"/api/v1/deliveries/{record_id}/approve",
        json={},
        headers={**org["headers_admin"], "Idempotency-Key": "appr-2"},
    )
    assert second.status_code == 200
    assert second.json()["status"] == "APPROVED"

    db = _make_session()
    try:
        deliveries = list(db.scalars(select(StockMovement).where(StockMovement.movement_type == "DELIVERY")))
        assert len(deliveries) == 1, "approval must be idempotent: exactly one DELIVERY movement"
        assert str(deliveries[0].quantity_kg) == "40.000"
    finally:
        db.close()


def test_reject_releases_reservation_without_stock_change(org_factory, client: TestClient):
    from io import BytesIO

    from PIL import Image

    org = org_factory()
    intent = client.post(
        "/api/v1/evidence/upload-intents", json={"content_type": "image/jpeg"}, headers=org["headers_dist"]
    ).json()
    buf = BytesIO()
    Image.new("RGB", (4, 4), (10, 200, 10)).save(buf, format="JPEG")
    client.put(intent["upload_url"], content=buf.getvalue(), headers=org["headers_dist"])
    submit = client.post(
        "/api/v1/deliveries",
        json={
            "assignment_id": org["assignment"]["id"],
            "quantity": "25",
            "unit": "KG",
            "evidence": [{"intent_id": intent["intent_id"], "capture_source": "CAMERA"}],
        },
        headers={**org["headers_dist"], "Idempotency-Key": "sub-rej"},
    )
    assert submit.status_code == 201
    record_id = submit.json()["id"]

    summary_before = client.get("/api/v1/inventory/summary", headers=org["headers_admin"]).json()
    dist_before = next(a for a in summary_before["accounts"] if a["account_type"] == "DISTRIBUTOR")

    # Rejecting is an admin action: unauthenticated callers must be refused,
    # and the record must remain reserved until the authorized reject lands.
    anonymous = client.post(
        f"/api/v1/deliveries/{record_id}/reject", json={"reason": "Quantity mismatch in the field."}
    )
    assert anonymous.status_code == 401, anonymous.text
    summary_between = client.get("/api/v1/inventory/summary", headers=org["headers_admin"]).json()
    dist_between = next(a for a in summary_between["accounts"] if a["account_type"] == "DISTRIBUTOR")
    assert float(dist_between["reserved_kg"]) == float(dist_before["reserved_kg"])

    reject = client.post(
        f"/api/v1/deliveries/{record_id}/reject",
        json={"reason": "Quantity mismatch in the field."},
        headers=org["headers_admin"],
    )
    assert reject.status_code == 200, reject.text
    assert reject.json()["status"] == "REJECTED"

    summary_after = client.get("/api/v1/inventory/summary", headers=org["headers_admin"]).json()
    dist_after = next(a for a in summary_after["accounts"] if a["account_type"] == "DISTRIBUTOR")
    assert float(dist_after["posted_balance_kg"]) == float(dist_before["posted_balance_kg"]), (
        "rejection must not change ledger balances"
    )
    assert float(dist_after["reserved_kg"]) == 0.0, "rejection must release the reservation"


def test_adjustment_requires_reason_and_blocks_negative(org_factory, client: TestClient):
    org = org_factory()
    summary = client.get("/api/v1/inventory/summary", headers=org["headers_admin"]).json()
    central = next(a for a in summary["accounts"] if a["account_type"] == "CENTRAL")

    no_reason = client.post(
        "/api/v1/inventory/adjustments",
        json={
            "account_id": central["id"],
            "quantity": "10",
            "unit": "KG",
            "movement_type": "LOSS",
            "reason": "  ",
        },
        headers=org["headers_admin"],
    )
    assert no_reason.status_code == 422 or no_reason.status_code == 400

    too_much = client.post(
        "/api/v1/inventory/adjustments",
        json={
            "account_id": central["id"],
            "quantity": "100000",
            "unit": "KG",
            "movement_type": "LOSS",
            "reason": "rodent damage",
        },
        headers=org["headers_admin"],
    )
    assert too_much.status_code == 409
    assert too_much.json()["error"]["code"] == "INSUFFICIENT_STOCK"


def test_reversal_is_compensating_and_append_only(org_factory, client: TestClient):
    org = org_factory()
    receipts = client.get(
        f"/api/v1/inventory/accounts/{_central_account_id(client, org)}/ledger", headers=org["headers_admin"]
    ).json()
    movement_id = receipts["items"][0]["id"]
    rev = client.post(
        f"/api/v1/inventory/movements/{movement_id}/reversal",
        json={"reason": "entry recorded against wrong lot"},
        headers=org["headers_admin"],
    )
    assert rev.status_code == 201, rev.text
    db = _make_session()
    try:
        reversal = db.execute(
            text("SELECT reversal_of_id, movement_type FROM stock_movements WHERE reversal_of_id = :id"),
            {"id": movement_id},
        ).fetchone()
        assert reversal is not None and reversal[1] == "REVERSAL"
        # append-only: UPDATE/DELETE must be rejected by DB triggers
        with pytest.raises(DBAPIError):
            db.execute(text("UPDATE stock_movements SET quantity_kg = 1 WHERE id = :id"), {"id": movement_id})
            db.commit()
        db.rollback()
    finally:
        db.close()


def _central_account_id(client: TestClient, org: dict) -> str:
    summary = client.get("/api/v1/inventory/summary", headers=org["headers_admin"]).json()
    return next(a for a in summary["accounts"] if a["account_type"] == "CENTRAL")["id"]


def test_reconciliation_balances(org_factory, client: TestClient):
    org = org_factory()
    summary = client.get("/api/v1/inventory/summary", headers=org["headers_admin"]).json()
    recon = summary["reconciliation"]
    assert recon is not None
    assert recon["balanced"] is True, recon


def test_unit_conversions_quintal_tonne_bag(org_factory, client: TestClient):
    org = org_factory()
    client.patch("/api/v1/settings", json={"kg_per_bag": "50"}, headers=org["headers_admin"])

    for unit, qty, expected in (
        ("QUINTAL", "2", "200.000"),
        ("TONNE", "0.5", "500.000"),
        ("BAG", "10", "500.000"),
    ):
        resp = client.post(
            "/api/v1/inventory/receipts",
            json={"quantity": qty, "unit": unit, "source_reference": f"unit-test-{unit}"},
            headers={**org["headers_admin"], "Idempotency-Key": f"unit-test-{unit}"},
        )
        assert resp.status_code == 201, (unit, resp.text)
        assert str(resp.json()["quantity_kg"]) == expected

    # 1 bag display conversion honors configured factor
    display = client.get(
        "/api/v1/inventory/display-unit",
        params={"quantity_kg": "500", "unit": "BAG"},
        headers=org["headers_admin"],
    )
    assert display.status_code == 200
    body = display.json()
    assert body["factor_label"] == "1 bag = 50 kg"

    # reject over-precise quantity
    resp = client.post(
        "/api/v1/inventory/receipts",
        json={"quantity": "12.34567", "unit": "KG", "source_reference": "precise"},
        headers={**org["headers_admin"], "Idempotency-Key": "unit-test-precise"},
    )
    assert resp.status_code == 422
