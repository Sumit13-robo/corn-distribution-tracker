"""Distribution submission: state machine, scoping, evidence binding, cancellation."""

from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image


def _upload_photo(client: TestClient, headers: dict, color=(120, 100, 40)) -> dict:
    intent = client.post(
        "/api/v1/evidence/upload-intents", json={"content_type": "image/jpeg"}, headers=headers
    ).json()
    buf = BytesIO()
    Image.new("RGB", (6, 6), color).save(buf, format="JPEG")
    put = client.put(intent["upload_url"], content=buf.getvalue(), headers=headers)
    assert put.status_code == 204, put.text
    return {
        "intent_id": intent["intent_id"],
        "capture_source": "CAMERA",
        "client_captured_at": "2026-10-21T10:00:00Z",
    }


def _submit(
    client: TestClient,
    org: dict,
    *,
    quantity: str = "20",
    key: str = "s1",
    evidence: list | None = None,
    location: dict | None = None,
    headers: dict | None = None,
):
    return client.post(
        "/api/v1/deliveries",
        json={
            "assignment_id": org["assignment"]["id"],
            "quantity": quantity,
            "unit": "KG",
            "evidence": evidence if evidence is not None else [_upload_photo(client, org["headers_dist"])],
            "location": location
            if location is not None
            else {
                "latitude": "12.5519",
                "longitude": "15.0002",
                "accuracy_m": "10",
                "timestamp": "2026-10-21T10:00:00Z",
            },
        },
        headers={**(headers or org["headers_dist"]), "Idempotency-Key": key},
    )


def test_submit_creates_pending_record_and_reservation(org_factory, client: TestClient):
    org = org_factory()
    response = _submit(client, org, key="sub-a")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "SUBMITTED"
    assert body["geo_status"] in {"PASS", "WARNING"}
    assert len(body["evidence"]) == 1

    summary = client.get("/api/v1/inventory/summary", headers=org["headers_dist"]).json()
    own = summary["accounts"][0]
    assert float(own["reserved_kg"]) == 20.0
    assert float(own["available_kg"]) == 80.0  # 100 allocated - 20 reserved


def test_duplicate_idempotency_key_returns_original_record(org_factory, client: TestClient):
    org = org_factory()
    first = _submit(client, org, key="dup-1")
    retry = _submit(client, org, key="dup-1")
    assert first.status_code == 201 and retry.status_code == 201
    assert first.json()["id"] == retry.json()["id"], (
        "retry after lost response must return the original record"
    )


def test_cannot_submit_for_another_distributor_assignment_by_id(org_factory, client: TestClient):
    """IDOR: a second distributor cannot submit against the first distributor's assignment."""
    org = org_factory()
    other_token = org["auth"].create_distributor(email="dist2@example.org", name="Other Field")
    headers_other = org["auth"].bearer(other_token)
    fabricated_intent = "00000000-0000-0000-0000-000000000000"
    submit = client.post(
        "/api/v1/deliveries",
        json={
            "assignment_id": org["assignment"]["id"],
            "quantity": "5",
            "unit": "KG",
            "evidence": [{"intent_id": fabricated_intent, "capture_source": "CAMERA"}],
        },
        headers={**headers_other, "Idempotency-Key": "foreign-1"},
    )
    # Either 404 (assignment not owned) or 404 (no stock account yet) — never 2xx.
    assert submit.status_code == 404, submit.text


def test_invalid_quantity_and_missing_evidence_rejected(org_factory, client: TestClient):
    org = org_factory()
    zero = _submit(client, org, quantity="0", key="q-zero")
    assert zero.status_code == 422

    no_evidence = _submit(client, org, evidence=[], key="e-missing")
    assert no_evidence.status_code == 422

    used_intent = client.post(
        "/api/v1/evidence/upload-intents", json={"content_type": "image/jpeg"}, headers=org["headers_dist"]
    ).json()
    fabricated = _submit(
        client,
        org,
        evidence=[{"intent_id": used_intent["intent_id"], "capture_source": "CAMERA"}],
        key="e-unuploaded",
    )
    assert fabricated.status_code in (400, 422, 404), fabricated.text


def test_insufficient_stock_submission_conflict(org_factory, client: TestClient):
    org = org_factory()  # 100 kg available
    response = _submit(client, org, quantity="150", key="over-1")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INSUFFICIENT_STOCK"


def test_cancel_releases_reservation(org_factory, client: TestClient):
    org = org_factory()
    submit = _submit(client, org, key="cancel-1")
    assert submit.status_code == 201
    record_id = submit.json()["id"]
    cancel = client.post(
        f"/api/v1/deliveries/{record_id}/cancel",
        json={"reason": "distributor retrace"},
        headers=org["headers_dist"],
    )
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["status"] == "CANCELLED"

    summary = client.get("/api/v1/inventory/summary", headers=org["headers_dist"]).json()
    assert float(summary["accounts"][0]["reserved_kg"]) == 0.0
