"""Distribution submission: state machine, scoping, evidence binding, cancellation."""

from __future__ import annotations

import pytest

from corn.models import DistributionRecord, StockMovement
from tests.conftest import AuthClient, json_request, submit_delivery, upload_png

pytestmark = pytest.mark.django_db


def account_for(client, account_type: str) -> dict:
    summary = client.get("/api/v1/inventory/summary").json()
    return next(account for account in summary["accounts"] if account["account_type"] == account_type)


def test_submit_creates_pending_record_and_reservation(org_factory):
    org = org_factory()
    evidence = upload_png(org["dist_client"])
    response = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="20",
        evidence=evidence,
        idempotency_key="sub-a",
    )
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["status"] == "SUBMITTED"
    assert body["geo_status"] in {"PASS", "WARNING"}
    assert len(body["evidence"]) == 1
    assert body["quantity_kg"] == "20.000"

    own = account_for(org["dist_client"], "DISTRIBUTOR")
    assert own["reserved_kg"] == "20.000"
    assert own["available_kg"] == "80.000"  # 100 allocated - 20 reserved


def test_duplicate_idempotency_key_returns_original_record(org_factory):
    org = org_factory()
    evidence = upload_png(org["dist_client"])
    first = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="20",
        evidence=evidence,
        idempotency_key="dup-1",
    )
    assert first.status_code == 201, first.content
    # The intent is already consumed; an idempotent retry must not re-read it.
    retry = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="20",
        evidence=evidence,
        idempotency_key="dup-1",
    )
    assert retry.status_code == 201, retry.content
    assert first.json()["id"] == retry.json()["id"]
    assert DistributionRecord.objects.count() == 1


def test_cannot_submit_for_another_distributor_assignment_by_id(org_factory):
    org = org_factory()
    other = AuthClient()
    other.create_distributor(email="dist2@example.org", name="Other Field")
    evidence = upload_png(other.client)
    response = submit_delivery(
        other.client,
        assignment_id=org["assignment"]["id"],
        quantity="5",
        evidence=evidence,
        idempotency_key="foreign-1",
    )
    assert response.status_code == 404, response.content


def test_invalid_quantity_and_missing_evidence_rejected(org_factory):
    org = org_factory()
    evidence = upload_png(org["dist_client"])
    zero = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="0",
        evidence=evidence,
        idempotency_key="q-zero",
    )
    assert zero.status_code == 422

    no_evidence = json_request(
        org["dist_client"],
        "post",
        "/api/v1/deliveries",
        {
            "assignment_id": org["assignment"]["id"],
            "quantity": "5",
            "unit": "KG",
            "evidence": [],
        },
        HTTP_IDEMPOTENCY_KEY="e-missing",
    )
    assert no_evidence.status_code == 422

    unused_intent = json_request(
        org["dist_client"],
        "post",
        "/api/v1/evidence/upload-intents",
        {"content_type": "image/png"},
    ).json()
    unuploaded = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="5",
        evidence={"intent_id": unused_intent["intent_id"], "capture_source": "CAMERA"},
        idempotency_key="e-unuploaded",
    )
    assert unuploaded.status_code == 400, unuploaded.content


def test_insufficient_stock_submission_conflict(org_factory):
    org = org_factory()
    evidence = upload_png(org["dist_client"])
    response = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="150",
        evidence=evidence,
        idempotency_key="over-1",
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INSUFFICIENT_STOCK"
    assert not DistributionRecord.objects.exists()


def test_cancel_releases_reservation(org_factory):
    org = org_factory()
    evidence = upload_png(org["dist_client"])
    submit = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="20",
        evidence=evidence,
        idempotency_key="cancel-1",
    )
    assert submit.status_code == 201, submit.content
    record_id = submit.json()["id"]
    cancel = json_request(
        org["dist_client"],
        "post",
        f"/api/v1/deliveries/{record_id}/cancel",
        {"reason": "distributor retrace"},
    )
    assert cancel.status_code == 200, cancel.content
    assert cancel.json()["status"] == "CANCELLED"
    own = account_for(org["dist_client"], "DISTRIBUTOR")
    assert own["reserved_kg"] == "0.000"


def test_distributor_cannot_approve_own_delivery(org_factory):
    org = org_factory()
    evidence = upload_png(org["dist_client"])
    submit = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="10",
        evidence=evidence,
        idempotency_key="self-approve",
    )
    record_id = submit.json()["id"]
    response = json_request(
        org["dist_client"],
        "post",
        f"/api/v1/deliveries/{record_id}/approve",
        {},
        HTTP_IDEMPOTENCY_KEY="self-approve-review",
    )
    assert response.status_code == 403


def test_outside_geofence_requires_exception_reason(org_factory):
    org = org_factory()
    evidence = upload_png(org["dist_client"])
    submit = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="10",
        evidence=evidence,
        idempotency_key="outside-1",
        latitude="12.700000",
        longitude="15.100000",
    )
    assert submit.status_code == 201, submit.content
    record = submit.json()
    assert "OUTSIDE_GEOFENCE" in record["geo_flags"]
    declined = json_request(
        org["admin_client"],
        "post",
        f"/api/v1/deliveries/{record['id']}/approve",
        {},
        HTTP_IDEMPOTENCY_KEY="outside-review-1",
    )
    assert declined.status_code == 409
    assert declined.json()["error"]["code"] == "REASON_REQUIRED"
    approved = json_request(
        org["admin_client"],
        "post",
        f"/api/v1/deliveries/{record['id']}/approve",
        {"exception_reason": "Site coordinates verified by district officer."},
        HTTP_IDEMPOTENCY_KEY="outside-review-2",
    )
    assert approved.status_code == 200, approved.content
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["review_exception_reason"]


def test_approved_record_posts_stock_and_cannot_be_cancelled(org_factory):
    org = org_factory()
    evidence = upload_png(org["dist_client"])
    submit = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="35",
        evidence=evidence,
        idempotency_key="approve-then-cancel",
    )
    record_id = submit.json()["id"]
    approved = json_request(
        org["admin_client"],
        "post",
        f"/api/v1/deliveries/{record_id}/approve",
        {},
        HTTP_IDEMPOTENCY_KEY="approve-1",
    )
    assert approved.status_code == 200, approved.content
    assert approved.json()["stock_movement_id"]
    assert StockMovement.objects.filter(movement_type="DELIVERY").count() == 1
    cancel = json_request(
        org["dist_client"], "post", f"/api/v1/deliveries/{record_id}/cancel", {}
    )
    assert cancel.status_code == 409

    own = account_for(org["admin_client"], "DISTRIBUTOR")
    assert own["posted_balance_kg"] == "65.000"
    assert own["reserved_kg"] == "0.000"


def test_upload_intent_is_bound_to_the_uploading_user(org_factory):
    org = org_factory()
    other = AuthClient()
    other.create_distributor(email="dist3@example.org", name="Third Field")
    foreign_intent = upload_png(other.client)
    response = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="5",
        evidence=foreign_intent,
        idempotency_key="foreign-intent",
    )
    assert response.status_code == 404
    assert not DistributionRecord.objects.exists()
