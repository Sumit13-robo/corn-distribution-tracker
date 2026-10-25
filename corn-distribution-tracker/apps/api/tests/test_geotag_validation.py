"""Geotag/photo validation flags and evidence upload constraints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import BytesIO

import pytest
from PIL import Image

from corn.errors import AppError
from corn.geo import evaluate_geo, geodesic_distance_m, haversine_m, validate_coordinates
from corn.services import evidence as evidence_service
from tests.conftest import json_request, submit_delivery, upload_bytes, upload_png

pytestmark = pytest.mark.django_db


def jpeg_bytes(color: tuple[int, int, int] = (140, 120, 60)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 6), color=color).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_haversine_known_distances():
    assert abs(haversine_m(Decimal("0"), Decimal("0"), Decimal("0"), Decimal("1")) - 111_195) < 50
    assert (
        abs(haversine_m(Decimal("0"), Decimal("0"), Decimal("90"), Decimal("0")) - 10_007_543) < 50
    )


def test_geodesic_known_distances():
    assert (
        abs(
            geodesic_distance_m(
                Decimal("0"), Decimal("0"), Decimal("0"), Decimal("1")
            )
            - 111_319
        )
        < 50
    )
    assert (
        abs(
            geodesic_distance_m(
                Decimal("0"), Decimal("0"), Decimal("90"), Decimal("0")
            )
            - 10_001_966
        )
        < 50
    )


def test_evaluate_geo_records_distance_without_location_warnings():
    result = evaluate_geo(
        latitude=Decimal("12.5518"),
        longitude=Decimal("15.1"),
        accuracy_m=Decimal("3"),
        location_timestamp=None,
        site_latitude=Decimal("12.5518"),
        site_longitude=Decimal("15.1"),
        geofence_radius_m=200,
        max_accuracy_m=100,
        max_age_seconds=300,
    )
    assert result["flags"] == []
    assert result["geo_status"] == "PASS"
    assert result["distance_m"] is not None and result["distance_m"] < 1

    far = evaluate_geo(
        latitude=Decimal("12.7"),
        longitude=Decimal("15.1"),
        accuracy_m=Decimal("500"),
        location_timestamp=datetime.now(UTC) - timedelta(minutes=30),
        site_latitude=Decimal("12.5518"),
        site_longitude=Decimal("15.1"),
        geofence_radius_m=200,
        max_accuracy_m=100,
        max_age_seconds=300,
    )
    assert far["flags"] == []
    assert far["geo_status"] == "PASS"
    assert int(far["distance_m"] or 0) > 16_000

    name_only_site = evaluate_geo(
        latitude=Decimal("12.5518"),
        longitude=Decimal("15.1"),
        accuracy_m=Decimal("3"),
        location_timestamp=datetime.now(UTC),
        site_latitude=None,
        site_longitude=None,
        geofence_radius_m=200,
        max_accuracy_m=100,
        max_age_seconds=300,
    )
    assert name_only_site["distance_m"] is None
    assert name_only_site["flags"] == []
    assert name_only_site["geo_status"] == "PASS"

    missing = evaluate_geo(
        latitude=None,
        longitude=None,
        accuracy_m=None,
        location_timestamp=None,
        site_latitude=Decimal("12.5518"),
        site_longitude=Decimal("15.1"),
        geofence_radius_m=200,
        max_accuracy_m=100,
        max_age_seconds=300,
    )
    assert missing["geo_status"] == "UNAVAILABLE" and missing["flags"] == []


def test_coordinate_range_validation():
    for bad_lat in ("90.5", "-91"):
        with pytest.raises(AppError, match="Latitude"):
            validate_coordinates(Decimal(bad_lat), Decimal("10.0"))


def test_name_only_site_submission_keeps_gps_but_skips_distance(org_factory):
    org = org_factory()
    cleared = json_request(
        org["admin_client"],
        "patch",
        f"/api/v1/sites/{org['site']['id']}",
        {"latitude": None, "longitude": None},
    )
    assert cleared.status_code == 200, cleared.content.decode()

    response = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="10",
        evidence=upload_png(org["dist_client"]),
        idempotency_key="name-only-site-1",
    )
    assert response.status_code == 201, response.content.decode()
    record = response.json()
    assert record["location_latitude"] == "12.551900"
    assert record["location_longitude"] == "15.100100"
    assert record["distance_to_site_m"] is None
    assert record["geo_flags"] == []
    assert record["geo_status"] == "PASS"


def test_exif_gps_difference_is_recorded_without_location_warning(monkeypatch, org_factory):
    org = org_factory()
    monkeypatch.setattr(
        evidence_service,
        "extract_exif",
        lambda data: {"latitude": 12.9, "longitude": 15.9, "taken_at": None},
    )
    evidence = upload_bytes(org["dist_client"], jpeg_bytes(), "image/jpeg")
    response = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="10",
        evidence=evidence,
        idempotency_key="exif-1",
    )
    assert response.status_code == 201, response.content
    evidence_body = response.json()["evidence"][0]
    assert "EXIF_GPS_MISMATCH" not in evidence_body["validation_flags"]
    assert evidence_body["metadata_check_result"]["exif_vs_reported_m"] > 0
    assert "EXIF_GPS_MISMATCH" not in response.json()["geo_flags"]


def test_duplicate_image_hash_is_flagged(org_factory):
    org = org_factory()
    data = jpeg_bytes(color=(9, 9, 9))
    first = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="5",
        evidence=upload_bytes(org["dist_client"], data, "image/jpeg"),
        idempotency_key="dup-img-1",
    )
    assert first.status_code == 201, first.content
    second = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="5",
        evidence=upload_bytes(org["dist_client"], data, "image/jpeg"),
        idempotency_key="dup-img-2",
        include_location=False,
    )
    assert second.status_code == 201, second.content
    assert "DUPLICATE_IMAGE_HASH" in second.json()["evidence"][0]["validation_flags"]


def test_unsupported_file_type_is_rejected_before_submission(org_factory):
    org = org_factory()
    intent = json_request(
        org["dist_client"],
        "post",
        "/api/v1/evidence/upload-intents",
        {"content_type": "image/jpeg"},
    ).json()
    put = org["dist_client"].put(
        intent["upload_url"], data=b"not actually an image", content_type="image/jpeg"
    )
    assert put.status_code == 400, put.content
    response = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="5",
        evidence={"intent_id": intent["intent_id"], "capture_source": "CAMERA"},
        idempotency_key="bad-type",
        include_location=False,
    )
    assert response.status_code == 400


def test_oversize_upload_is_rejected(org_factory):
    org = org_factory()
    big = jpeg_bytes() + b"\x00" * 1_200_000
    intent = json_request(
        org["dist_client"],
        "post",
        "/api/v1/evidence/upload-intents",
        {"content_type": "image/jpeg"},
    ).json()
    put = org["dist_client"].put(
        intent["upload_url"], data=big, content_type="image/jpeg"
    )
    assert put.status_code == 400


def test_no_exif_is_informational(org_factory):
    org = org_factory()
    response = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="10",
        evidence=upload_png(org["dist_client"]),
        idempotency_key="no-exif-1",
    )
    assert response.status_code == 201, response.content
    assert response.json()["evidence"][0]["metadata_check_result"]["exif"] == "absent"


def test_stale_and_inaccurate_location_do_not_emit_warnings(org_factory):
    org = org_factory()
    old = (datetime.now(UTC) - timedelta(minutes=30)).isoformat()
    response = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="10",
        evidence=upload_png(org["dist_client"]),
        idempotency_key="stale-1",
        accuracy="500",
        timestamp=old,
    )
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["geo_flags"] == []
    assert body["geo_status"] == "PASS"
    assert body["location_accuracy_m"] == "500.00"


def test_missing_location_is_allowed_without_a_warning(org_factory):
    org = org_factory()
    response = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="10",
        evidence=upload_png(org["dist_client"]),
        idempotency_key="missing-location-1",
        include_location=False,
    )
    assert response.status_code == 201, response.content
    assert response.json()["geo_status"] == "UNAVAILABLE"
    assert response.json()["geo_flags"] == []


def test_capture_time_drift_is_flagged(org_factory):
    org = org_factory()
    evidence = upload_png(org["dist_client"])
    evidence["client_captured_at"] = "2026-10-21T10:00:00Z"
    response = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="10",
        evidence=evidence,
        idempotency_key="drift-1",
    )
    assert response.status_code == 201, response.content
    assert "CAPTURE_TIME_MISMATCH" in response.json()["evidence"][0]["validation_flags"]


def test_location_range_is_rejected_at_the_boundary(org_factory):
    org = org_factory()
    response = submit_delivery(
        org["dist_client"],
        assignment_id=org["assignment"]["id"],
        quantity="10",
        evidence=upload_png(org["dist_client"]),
        idempotency_key="bad-lat",
        latitude="90.5",
    )
    assert response.status_code == 422
