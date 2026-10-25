"""Campaign setup with name-only sites and optional site reference points."""

from __future__ import annotations

import pytest

from tests.conftest import AuthClient, json_request

pytestmark = pytest.mark.django_db


def _create_campaign(client, *, name: str, reference_code: str, sites: list[str] | None = None) -> dict:
    payload = {
        "name": name,
        "reference_code": reference_code,
        "timezone": "Asia/Kolkata",
        "status": "DRAFT",
    }
    if sites is not None:
        payload["sites"] = sites
    response = json_request(client, "post", "/api/v1/campaigns", payload)
    assert response.status_code == 201, response.content.decode()
    return response.json()


def _campaign_sites(admin, campaign_id: str) -> list[dict]:
    response = json_request(admin, "get", f"/api/v1/sites?campaign_id={campaign_id}&limit=100")
    assert response.status_code == 200, response.content.decode()
    return response.json()["items"]


def test_campaign_setup_creates_name_only_sites_transactionally():
    admin = AuthClient()
    admin.create_admin()

    campaign = _create_campaign(
        admin.client,
        name="Kolhapur",
        reference_code="KOLHAPUR-1",
        sites=["Gandhi Chowk", "Rukadi Market", " gandhi chowk "],
    )

    sites = _campaign_sites(admin.client, campaign["id"])
    assert [site["name"] for site in sites] == ["Gandhi Chowk", "Rukadi Market"]
    assert all(site["campaign_id"] == campaign["id"] for site in sites)
    assert all(site["latitude"] is None and site["longitude"] is None for site in sites)
    assert all(site["site_code"] for site in sites)
    assert len({site["site_code"] for site in sites}) == 2


def test_site_name_only_auto_code_duplicate_and_optional_location_later():
    admin = AuthClient()
    admin.create_admin()
    campaign = _create_campaign(
        admin.client,
        name="Kolhapur",
        reference_code="KOLHAPUR-2",
        sites=[],
    )

    created = json_request(
        admin.client,
        "post",
        "/api/v1/sites",
        {"name": "Gandhi Chowk", "campaign_id": campaign["id"]},
    )
    assert created.status_code == 201, created.content.decode()
    site = created.json()
    assert site["site_code"] == "GANDHI-CHOWK"
    assert site["latitude"] is None and site["longitude"] is None

    duplicate = json_request(
        admin.client,
        "post",
        "/api/v1/sites",
        {"name": "gandhi chowk", "campaign_id": campaign["id"]},
    )
    assert duplicate.status_code == 400, duplicate.content.decode()

    partial_location = json_request(
        admin.client,
        "post",
        "/api/v1/sites",
        {"name": "Partial Location", "campaign_id": campaign["id"], "latitude": "16.7"},
    )
    assert partial_location.status_code in {400, 422}

    location = json_request(
        admin.client,
        "patch",
        f"/api/v1/sites/{site['id']}",
        {"latitude": "16.700000", "longitude": "74.243300"},
    )
    assert location.status_code == 200, location.content.decode()
    assert location.json()["latitude"] == "16.700000"
    assert location.json()["longitude"] == "74.243300"

    cleared = json_request(
        admin.client,
        "patch",
        f"/api/v1/sites/{site['id']}",
        {"latitude": None, "longitude": None},
    )
    assert cleared.status_code == 200, cleared.content.decode()
    assert cleared.json()["latitude"] is None and cleared.json()["longitude"] is None

    another = json_request(
        admin.client,
        "post",
        "/api/v1/sites",
        {"name": "Another site", "campaign_id": campaign["id"]},
    )
    assert another.status_code == 201, another.content.decode()
    duplicate_rename = json_request(
        admin.client,
        "patch",
        f"/api/v1/sites/{site['id']}",
        {"name": "another site"},
    )
    assert duplicate_rename.status_code == 400, duplicate_rename.content.decode()

    second_campaign = _create_campaign(
        admin.client,
        name="Second campaign",
        reference_code="KOLHAPUR-3",
        sites=[],
    )
    same_name_elsewhere = json_request(
        admin.client,
        "post",
        "/api/v1/sites",
        {"name": "Gandhi Chowk", "campaign_id": second_campaign["id"]},
    )
    assert same_name_elsewhere.status_code == 201, same_name_elsewhere.content.decode()
    assert same_name_elsewhere.json()["site_code"] != site["site_code"]


def test_analytics_campaign_filter_excludes_other_campaign_and_name_only_sites():
    admin = AuthClient()
    admin.create_admin()
    first = _create_campaign(
        admin.client, name="First", reference_code="ANALYTICS-1", sites=[]
    )
    second = _create_campaign(
        admin.client, name="Second", reference_code="ANALYTICS-2", sites=[]
    )

    located = json_request(
        admin.client,
        "post",
        "/api/v1/sites",
        {
            "name": "Located site",
            "campaign_id": first["id"],
            "latitude": "4.851000",
            "longitude": "31.582000",
        },
    )
    assert located.status_code == 201, located.content.decode()
    located_site = located.json()
    other = json_request(
        admin.client,
        "post",
        "/api/v1/sites",
        {
            "name": "Other campaign site",
            "campaign_id": second["id"],
            "latitude": "16.700000",
            "longitude": "74.243300",
        },
    )
    assert other.status_code == 201, other.content.decode()
    name_only = json_request(
        admin.client,
        "post",
        "/api/v1/sites",
        {"name": "Name-only site", "campaign_id": first["id"]},
    )
    assert name_only.status_code == 201, name_only.content.decode()
    name_only_site = name_only.json()

    map_response = json_request(
        admin.client, "get", f"/api/v1/analytics/map-sites?campaign_id={first['id']}"
    )
    assert map_response.status_code == 200, map_response.content.decode()
    assert {row["id"] for row in map_response.json()} == {located_site["id"]}

    site_rows = json_request(
        admin.client, "get", f"/api/v1/analytics/sites?campaign_id={first['id']}"
    )
    assert site_rows.status_code == 200, site_rows.content.decode()
    rows = site_rows.json()
    assert {row["site_name"] for row in rows} == {"Located site", "Name-only site"}
    assert name_only_site["id"] in {row["site_id"] for row in rows}


def test_assignment_rejects_site_belonging_to_another_campaign():
    admin = AuthClient()
    admin.create_admin()
    distributor = AuthClient()
    distributor_user = distributor.create_distributor()

    first = _create_campaign(
        admin.client, name="First", reference_code="SCOPE-1", sites=["First Site"]
    )
    first_site = _campaign_sites(admin.client, first["id"])[0]
    second = _create_campaign(
        admin.client, name="Second", reference_code="SCOPE-2", sites=["Second Site"]
    )
    second_site = _campaign_sites(admin.client, second["id"])[0]

    valid = json_request(
        admin.client,
        "post",
        "/api/v1/assignments",
        {
            "site_id": first_site["id"],
            "campaign_id": first["id"],
            "distributor_user_id": distributor_user["id"],
            "target_quantity": "10",
            "unit": "KG",
        },
    )
    assert valid.status_code == 201, valid.content.decode()

    mismatched = json_request(
        admin.client,
        "post",
        "/api/v1/assignments",
        {
            "site_id": second_site["id"],
            "campaign_id": first["id"],
            "distributor_user_id": distributor_user["id"],
            "target_quantity": "10",
            "unit": "KG",
        },
    )
    assert mismatched.status_code == 400, mismatched.content.decode()
    assert "another campaign" in mismatched.content.decode()
