"""Analytics scope/formula tests, CSV escaping, audit trail and settings."""

from __future__ import annotations

import csv
import io

import pytest

from corn.models import DistributionSite
from tests.conftest import json_request, submit_delivery, upload_png

pytestmark = pytest.mark.django_db


def submit(org, *, quantity: str, key: str, include_location: bool = True):
    response = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity=quantity,
        evidence=upload_png(org["dist_client"], color=(int(quantity), 100, 50)),
        idempotency_key=key,
        include_location=include_location,
    )
    assert response.status_code == 201, response.content
    return response.json()


def test_overview_formulas_distinguish_pending_and_approved(org_factory):
    org = org_factory()
    submit(org, quantity="30", key="an-1")
    approved = submit(org, quantity="20", key="an-2")
    approved_response = json_request(
        org["admin_client"],
        "post",
        f"/api/v1/deliveries/{approved['id']}/approve",
        {},
        HTTP_IDEMPOTENCY_KEY="an-approve",
    )
    assert approved_response.status_code == 200, approved_response.content

    overview = org["admin_client"].get("/api/v1/analytics/overview").json()
    assert overview["submitted_pending_kg"] == "30.000"
    assert overview["approved_delivered_kg"] == "20.000"
    assert overview["stock"]["central_on_hand_kg"] == "400.000"
    assert overview["stock"]["distributor_held_kg"] == "80.000"
    assert overview["stock"]["site_stock_kg"] == "20.000"
    assert overview["remaining_target_kg"] == "130.000"
    assert overview["open_review_count"] == 1
    assert overview["evidence_completeness"]["approved_with_evidence"] == 1
    assert overview["evidence_completeness"]["approved_total"] == 1
    assert overview["target_kg"] == "150.000"

    mine = org["dist_client"].get("/api/v1/analytics/overview")
    assert mine.status_code == 200
    assert mine.json()["stock"]["central_on_hand_kg"] == "0.000"
    assert mine.json()["approved_delivered_kg"] == "20.000"
    other = org["dist_client"].get("/api/v1/analytics/distributors")
    assert other.status_code == 403


def test_distributor_performance_denominators(org_factory):
    org = org_factory()
    submit(org, quantity="10", key="perf-1")
    rows = org["admin_client"].get("/api/v1/analytics/distributors").json()
    row = next(r for r in rows if r["distributor_user_id"] == org["distributor_user_id"])
    assert row["target_kg"] == "150.000"
    assert row["pending_kg"] == "10.000"
    assert row["submitted_kg"] == "10.000"
    assert row["denominator_note"]


def test_map_sites_status_and_bbox(org_factory):
    org = org_factory()
    submit(org, quantity="10", key="map-1")
    rows = org["admin_client"].get("/api/v1/analytics/map-sites").json()
    row = next(r for r in rows if r["site_code"] == "ND-01")
    assert row["status"] == "PENDING"
    assert row["pending_kg"] == "10.000" and row["target_kg"] == "150.000"

    empty = org["admin_client"].get("/api/v1/analytics/map-sites?bbox=0,0,1,1")
    assert empty.status_code == 200 and empty.json() == []

    bad = org["admin_client"].get("/api/v1/analytics/map-sites?bbox=1,1,0,0")
    assert bad.status_code == 422


def test_map_deliveries_only_returns_captured_delivery_points(org_factory):
    org = org_factory()
    located = submit(org, quantity="12", key="mapd-located")
    submit(org, quantity="13", key="mapd-no-location", include_location=False)

    response = org["admin_client"].get("/api/v1/analytics/map-deliveries")
    assert response.status_code == 200
    rows = response.json()
    assert [row["id"] for row in rows] == [located["id"]]
    row = rows[0]
    assert row["site_code"] == "ND-01"
    assert row["site_name"] == "North Depot"
    assert row["distributor_name"] == "Field Distributor"
    assert row["campaign_id"] is None
    assert row["status"] == "SUBMITTED"
    assert row["quantity_kg"] == "12.000"
    assert row["location_latitude"] == "12.551900"
    assert row["location_longitude"] == "15.100100"
    assert row["location_accuracy_m"] == "8.00"

    assert org["dist_client"].get("/api/v1/analytics/map-deliveries").status_code == 403
    empty = org["admin_client"].get("/api/v1/analytics/map-deliveries?bbox=0,0,1,1")
    assert empty.status_code == 200 and empty.json() == []
    bad = org["admin_client"].get("/api/v1/analytics/map-deliveries?bbox=1,1,0,0")
    assert bad.status_code == 422

    approved = json_request(
        org["admin_client"],
        "post",
        f"/api/v1/deliveries/{located['id']}/approve",
        {},
        HTTP_IDEMPOTENCY_KEY="mapd-approve",
    )
    assert approved.status_code == 200, approved.content
    rows = org["admin_client"].get("/api/v1/analytics/map-deliveries").json()
    assert len(rows) == 1 and rows[0]["status"] == "APPROVED"

    rejected = submit(org, quantity="14", key="mapd-rejected")
    reject_response = json_request(
        org["admin_client"],
        "post",
        f"/api/v1/deliveries/{rejected['id']}/reject",
        {"reason": "Rejected test claim"},
        HTTP_IDEMPOTENCY_KEY="mapd-reject",
    )
    assert reject_response.status_code == 200, reject_response.content
    rows = org["admin_client"].get("/api/v1/analytics/map-deliveries").json()
    assert [row["id"] for row in rows] == [located["id"]]


def test_csv_export_formula_escaping_audit_and_offset(org_factory):
    org = org_factory()
    DistributionSite.objects.filter(site_code="ND-01").update(
        name="=HYPERLINK(http://evil.example)"
    )
    submit(org, quantity="5", key="csv-1")
    response = org["admin_client"].get("/api/v1/exports/distributions.csv")
    assert response.status_code == 200
    assert "text/csv" in response["content-type"]
    rows = list(csv.reader(io.StringIO(response.content.decode())))
    assert rows[0][0] == "record_id"
    formula_cells = [
        cell
        for row in rows[1:]
        for cell in row
        if cell.startswith(("=", "+", "-", "@"))
    ]
    assert formula_cells == []
    escaped = [cell for row in rows[1:] for cell in row if cell.startswith("'")]
    assert any(cell == "'=HYPERLINK(http://evil.example)" for cell in escaped)
    # The timestamp is valid ISO-8601 rather than the old "…+00:00-utc" suffix.
    submitted_at = rows[1][1]
    assert submitted_at.endswith("Z") and not submitted_at.endswith("-utc")

    denied = org["dist_client"].get("/api/v1/exports/distributions.csv")
    assert denied.status_code == 403

    events = org["admin_client"].get(
        "/api/v1/audit/events?action=export.distributions&limit=1"
    ).json()
    assert events["total"] >= 1
    assert len(events["items"]) == 1
    # Offset must page, not crash or repeat the first row indefinitely.
    second = org["admin_client"].get(
        "/api/v1/audit/events?action=export.distributions&limit=1&offset=10"
    ).json()
    assert second["items"] == []


def test_audit_trail_records_sensitive_actions(org_factory):
    org = org_factory()
    submitted = submit(org, quantity="5", key="audit-1")
    reject = json_request(
        org["admin_client"],
        "post",
        f"/api/v1/deliveries/{submitted['id']}/reject",
        {"reason": "Blurred photo."},
    )
    assert reject.status_code == 200, reject.content

    events = org["admin_client"].get("/api/v1/audit/events?limit=100").json()
    actions = {event["action"] for event in events["items"]}
    assert {
        "distribution.submitted",
        "distribution.rejected",
        "stock.received",
        "stock.allocated",
        "auth.login",
    } <= actions
    denied = org["dist_client"].get("/api/v1/audit/events")
    assert denied.status_code == 403

    bad_filter = org["admin_client"].get("/api/v1/audit/events?from=not-a-date")
    assert bad_filter.status_code == 422


def test_settings_allowlist_and_auditing(org_factory):
    org = org_factory()
    ok = json_request(
        org["admin_client"],
        "patch",
        "/api/v1/settings",
        {
            "default_display_unit": "QUINTAL",
            "kg_per_bag": "50",
            "max_acceptable_gps_accuracy_m": "80",
        },
    )
    assert ok.status_code == 200, ok.content
    body = ok.json()
    assert body["default_display_unit"] == "QUINTAL"
    assert body["kg_per_bag"] == "50.00"

    intrude = json_request(
        org["admin_client"],
        "patch",
        "/api/v1/settings",
        {"storage_access_key_id": "sneaky"},
    )
    assert intrude.status_code == 422

    denied = org["dist_client"].patch(
        "/api/v1/settings", data='{"timezone":"UTC"}', content_type="application/json"
    )
    assert denied.status_code == 403
    visible = org["dist_client"].get("/api/v1/settings")
    assert visible.status_code == 200
