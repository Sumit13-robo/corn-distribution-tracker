"""Analytics scope/formula tests + CSV export escaping + audit trail."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _submit(client: TestClient, org: dict, *, quantity: str, key: str, location: dict | None = None):
    from io import BytesIO

    from PIL import Image

    intent = client.post(
        "/api/v1/evidence/upload-intents", json={"content_type": "image/jpeg"}, headers=org["headers_dist"]
    ).json()
    buf = BytesIO()
    Image.new("RGB", (5, 5), (90, 140, 50)).save(buf, format="JPEG")
    assert (
        client.put(intent["upload_url"], content=buf.getvalue(), headers=org["headers_dist"]).status_code
        == 204
    )
    return client.post(
        "/api/v1/deliveries",
        json={
            "assignment_id": org["assignment"]["id"],
            "quantity": quantity,
            "unit": "KG",
            "evidence": [{"intent_id": intent["intent_id"], "capture_source": "CAMERA"}],
            "location": location,
        },
        headers={**org["headers_dist"], "Idempotency-Key": key},
    )


def test_overview_formulas_distinguish_pending_and_approved(org_factory, client: TestClient):
    org = org_factory()
    pending = _submit(client, org, quantity="30", key="an-1")  # stays pending
    approved = _submit(client, org, quantity="20", key="an-2")
    assert pending.status_code == 201 and approved.status_code == 201
    # No location -> GPS_MISSING is a critical flag, so the approve call must
    # carry the explicit exception reason the review contract requires.
    ok = client.post(
        f"/api/v1/deliveries/{approved.json()['id']}/approve",
        json={"exception_reason": "GPS unavailable on device; reviewed manually."},
        headers=org["headers_admin"],
    )
    assert ok.status_code == 200, ok.text

    overview = client.get("/api/v1/analytics/overview", headers=org["headers_admin"]).json()
    assert float(overview["submitted_pending_kg"]) == 30.0, overview
    assert float(overview["approved_delivered_kg"]) == 20.0
    assert float(overview["stock"]["central_on_hand_kg"]) == 400.0  # 500 - 100 allocated
    assert float(overview["stock"]["distributor_held_kg"]) == 80.0  # 100 - 20 delivered
    assert float(overview["stock"]["site_stock_kg"]) == 20.0
    assert float(overview["remaining_target_kg"]) == 130.0  # 150 - 20
    assert overview["open_review_count"] == 1

    # distributor role capability check: scoped overview allowed, lists admin-only analytics
    mine = client.get("/api/v1/analytics/overview", headers=org["headers_dist"])
    assert mine.status_code == 200
    other = client.get("/api/v1/analytics/distributors", headers=org["headers_dist"])
    assert other.status_code == 403


def test_distributor_performance_denominators(org_factory, client: TestClient):
    org = org_factory()
    _submit(client, org, quantity="10", key="perf-1")
    rows = client.get("/api/v1/analytics/distributors", headers=org["headers_admin"]).json()
    row = next(r for r in rows if r["distributor_user_id"] == org["distributor_user_id"])
    assert float(row["target_kg"]) == 150.0
    assert float(row["pending_kg"]) == 10.0
    assert row["denominator_note"], "denominators must be explicit"


def test_map_sites_status_and_bbox(org_factory, client: TestClient):
    org = org_factory()
    _submit(client, org, quantity="10", key="map-1")
    rows = client.get("/api/v1/analytics/map-sites", headers=org["headers_admin"]).json()
    row = next(r for r in rows if r["site_code"] == "ND-01")
    assert row["status"] == "PENDING"
    assert float(row["pending_kg"]) == 10.0 and float(row["target_kg"]) == 150.0

    empty = client.get(
        "/api/v1/analytics/map-sites", params={"bbox": "0,0,1,1"}, headers=org["headers_admin"]
    ).json()
    assert empty == []  # bbox away from the site returns no rows (server-side filtering)

    bad = client.get("/api/v1/analytics/map-sites", params={"bbox": "1,1,0,0"}, headers=org["headers_admin"])
    assert bad.status_code == 422


def test_csv_export_formula_escaping_and_audit(org_factory, client: TestClient):
    org = org_factory()
    # Submit with a site whose name would start with "=" after export... sites are seeded, so
    # rename a distributor to a formula-like string in DB to simulate CSV injection attempts.
    import csv as csv_module
    import io as io_module

    from sqlalchemy import text as sa_text

    from tests.conftest import _make_session

    db = _make_session()
    try:
        db.execute(
            sa_text(
                "UPDATE distribution_sites SET name = '=HYPERLINK(http://evil)' WHERE site_code = 'ND-01'"
            )
        )
        db.commit()
    finally:
        db.close()

    _submit(client, org, quantity="5", key="csv-1")
    resp = client.get("/api/v1/exports/distributions.csv", headers=org["headers_admin"])
    assert resp.status_code == 200, resp.text
    assert "text/csv" in resp.headers["content-type"]
    content = resp.text
    rows = list(csv_module.reader(io_module.StringIO(content)))
    # Escape contract: a dangerous leading character must be apostrophe-prefixed.
    formula_cells = [c for row in rows[1:] for c in row if c.startswith(("=", "+", "-", "@"))]
    assert formula_cells == [], "CSV must escape formula-leading cells"
    escaped = [c for row in rows[1:] for c in row if c.startswith("'")]
    assert escaped, "escaped cells must be present"
    assert any(c == "'=HYPERLINK(http://evil)" for c in escaped)
    # Export access denied for distributors
    denied = client.get("/api/v1/exports/distributions.csv", headers=org["headers_dist"])
    assert denied.status_code == 403

    events = client.get(
        "/api/v1/audit/events", params={"action": "export.distributions"}, headers=org["headers_admin"]
    ).json()
    assert events["total"] >= 1


def test_audit_trail_records_sensitive_actions(org_factory, client: TestClient):
    org = org_factory()
    response = _submit(client, org, quantity="5", key="audit-1")
    record_id = response.json()["id"]
    reject = client.post(
        f"/api/v1/deliveries/{record_id}/reject",
        json={"reason": "Blurred photo."},
        headers=org["headers_admin"],
    )
    assert reject.status_code == 200

    events = client.get("/api/v1/audit/events", headers=org["headers_admin"]).json()
    actions = {e["action"] for e in events["items"]}
    assert {"distribution.submitted", "distribution.rejected", "stock.received", "stock.allocated"} & actions
    # audit endpoint is admin-only
    denied = client.get("/api/v1/audit/events", headers=org["headers_dist"])
    assert denied.status_code == 403


def test_settings_allowlist_and_auditing(org_factory, client: TestClient):
    org = org_factory()
    ok = client.patch(
        "/api/v1/settings",
        json={"default_display_unit": "QUINTAL", "kg_per_bag": "50", "max_acceptable_gps_accuracy_m": "80"},
        headers=org["headers_admin"],
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    # Compare numerically: the NUMERIC(8,2) column serializes with trailing zeros.
    assert body["default_display_unit"] == "QUINTAL" and float(body["kg_per_bag"]) == 50.0

    intrude = client.patch(
        "/api/v1/settings", json={"storage_access_key_id": "sneaky"}, headers=org["headers_admin"]
    )
    assert intrude.status_code == 422, "settings must be strictly allowlisted"

    denied = client.get("/api/v1/settings", headers=org["headers_dist"])
    assert denied.status_code == 200  # distributors may read visible org settings
