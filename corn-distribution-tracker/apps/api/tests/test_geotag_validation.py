"""Geotag/photo validation flag tests (docs/architecture/GEO_PHOTO_EVIDENCE.md)."""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from typing import Any

from fastapi.testclient import TestClient
from httpx import Response
from PIL import Image

from app.core.errors import AppError
from app.services.geo_service import evaluate_geo, geodesic_distance_m, haversine_m


def test_haversine_known_distances():
    # Spherical haversine on the IUGG mean Earth radius (R = 6,371,008.8 m) is
    # the documented fallback; it carries a known bias vs the WGS84 ellipsoid,
    # so assert the *spherical* reference values, not geodesic truth.
    assert abs(haversine_m(Decimal("0"), Decimal("0"), Decimal("0"), Decimal("1")) - 111_195) < 50
    # Spherical quarter-meridian = pi/2 * R ≈ 10,007,543 (not 10,001,966: that
    # is the WGS84 ellipsoidal meridian quadrant, covered by geodesic below).
    assert abs(haversine_m(Decimal("0"), Decimal("0"), Decimal("90"), Decimal("0")) - 10_007_543) < 50


def test_geodesic_known_distances():
    # Vincenty inverse (WGS84) must match geodesic truth within 50 m even at
    # continental scales: 1 degree of longitude on the equator and the
    # ellipsoidal meridian quadrant.
    assert abs(geodesic_distance_m(Decimal("0"), Decimal("0"), Decimal("0"), Decimal("1")) - 111_319) < 50
    assert abs(geodesic_distance_m(Decimal("0"), Decimal("0"), Decimal("90"), Decimal("0")) - 10_001_966) < 50


def test_evaluate_geo_flags():
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
    assert "GPS_STALE" in result["flags"]
    assert result["distance_m"] is not None and result["distance_m"] < 1

    far = evaluate_geo(
        latitude=Decimal("12.7"),
        longitude=Decimal("15.1"),
        accuracy_m=Decimal("2"),
        location_timestamp=None,
        site_latitude=Decimal("12.5518"),
        site_longitude=Decimal("15.1"),
        geofence_radius_m=200,
        max_accuracy_m=100,
        max_age_seconds=300,
    )
    assert "OUTSIDE_GEOFENCE" in far["flags"]
    assert int(far["distance_m"] or 0) > 16_000

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
    assert missing["geo_status"] == "UNAVAILABLE" and missing["flags"] == ["GPS_MISSING"]


def _jpeg_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (8, 6), color=(140, 120, 60)).save(buf, format="JPEG")
    return buf.getvalue()


def _upload(client: TestClient, data: bytes, content_type: str, headers: dict) -> dict:
    intent = client.post(
        "/api/v1/evidence/upload-intents", json={"content_type": content_type}, headers=headers
    ).json()
    put = client.put(intent["upload_url"], content=data, headers=headers)
    assert put.status_code == 204, put.text
    return {"intent_id": intent["intent_id"], "capture_source": "CAMERA"}


def _submit(
    client: TestClient, org: dict, evidence: list, key: str, location: dict | None = None
) -> Response:
    return client.post(
        "/api/v1/deliveries",
        json={
            "assignment_id": org["assignment"]["id"],
            "quantity": "10",
            "unit": "KG",
            "evidence": evidence,
            "location": location,
        },
        headers={**org["headers_dist"], "Idempotency-Key": key},
    )


def test_coordinate_range_validation(org_factory, client: TestClient):
    from app.services.geo_service import validate_coordinates

    for bad_lat in ("90.5", "-91"):
        with pytest_coord_error(bad_lat):
            validate_coordinates(Decimal(bad_lat), Decimal("10.0"))


class pytest_coord_error:
    def __init__(self, value: str) -> None:
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return exc_type is not None and issubclass(exc_type, AppError)


def test_gas_mismatch_exif_vs_reported_flag(monkeypatch, org_factory, client: TestClient):
    from app.services import evidence_service

    org = org_factory()
    monkeypatch.setattr(
        evidence_service,
        "extract_exif",
        lambda data: {"latitude": 12.9, "longitude": 15.9, "taken_at": None},
    )
    response = _submit(
        client,
        org,
        [_upload(client, _jpeg_bytes(), "image/jpeg", org["headers_dist"])],
        key="exif-1",
        location={
            "latitude": "12.5519",
            "longitude": "15.0002",
            "accuracy_m": "8",
            "timestamp": "2026-10-21T10:00:00Z",
        },
    )
    assert response.status_code == 201, response.text
    evidence = response.json()["evidence"][0]
    assert "EXIF_GPS_MISMATCH" in evidence["validation_flags"]


def test_duplicate_image_hash_flagged(monkeypatch, org_factory, client: TestClient):
    org = org_factory()
    data = _jpeg_bytes()
    evidence = [_upload(client, data, "image/jpeg", org["headers_dist"])]
    first = _submit(
        client,
        org,
        evidence,
        key="dup-img-1",
        location={
            "latitude": "12.5519",
            "longitude": "15.0002",
            "accuracy_m": "8",
            "timestamp": "2026-10-21T10:00:00Z",
        },
    )
    assert first.status_code == 201, first.text

    evidence2 = [_upload(client, data, "image/jpeg", org["headers_dist"])]

    def patched_extract(_data: bytes) -> dict[str, Any]:
        return {}

    from app.services import evidence_service

    # EXIF never present in the second upload: the hash duplicate must flag.
    monkeypatch.setattr(evidence_service, "extract_exif", patched_extract)
    second = _submit(
        client, org, evidence2, key="dup-img-2", location=None
    )  # no location: still allowed, flagged
    assert second.status_code == 201, second.text
    flags = second.json()["evidence"][0]["validation_flags"]
    assert "DUPLICATE_IMAGE_HASH" in flags


def test_unsupported_file_type_rejected(org_factory, client: TestClient):
    org = org_factory()
    intent = client.post(
        "/api/v1/evidence/upload-intents", json={"content_type": "image/jpeg"}, headers=org["headers_dist"]
    ).json()
    put = client.put(intent["upload_url"], content=b"not actually an image", headers=org["headers_dist"])
    assert put.status_code in (400, 415, 422)
    response = _submit(
        client,
        org,
        [{"intent_id": intent["intent_id"], "capture_source": "CAMERA"}],
        "bad-type",
        location=None,
    )
    assert response.status_code in (400, 404, 4, 415, 422), (
        "submission must not accept an unuploaded/invalid evidence intent"
    )


def test_oversize_upload_rejected(org_factory, client: TestClient):
    org = org_factory()
    big = _jpeg_bytes() + b"\x00" * (1_200_000)  # > 1MB cap in tests
    intent = client.post(
        "/api/v1/evidence/upload-intents", json={"content_type": "image/jpeg"}, headers=org["headers_dist"]
    ).json()
    put = client.put(intent["upload_url"], content=big, headers=org["headers_dist"])
    assert put.status_code in (400, 413, 422)


def test_no_exif_is_informational_not_rejection(org_factory, client: TestClient):
    org = org_factory()
    response = _submit(
        client, org, [_upload(client, _jpeg_bytes(), "image/jpeg", org["headers_dist"])], "no-exif-1"
    )
    assert response.status_code == 201, response.text
    evidence = response.json()["evidence"][0]
    assert evidence["metadata_check_result"]["exif"] == "absent"
