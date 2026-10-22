"""Geodesic distance and GPS/EXIF evidence evaluation.

Uses Vincenty's inverse method on WGS84 with the documented haversine fallback
for near-antipodal pairs. GPS/EXIF are indicators, not proof of authenticity.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from .enums import GeoFlag, GeoStatus
from .errors import AppError

EARTH_RADIUS_M = 6_371_008.8
_WGS84_A = 6_378_137.0
_WGS84_F = 1.0 / 298.257223563
_WGS84_B = _WGS84_A * (1.0 - _WGS84_F)


def validate_coordinates(
    latitude: Decimal | str | float,
    longitude: Decimal | str | float,
    *,
    field_lat: str = "latitude",
    field_lng: str = "longitude",
) -> tuple[Decimal, Decimal]:
    lat = Decimal(str(latitude))
    lng = Decimal(str(longitude))
    if not (-90 <= lat <= 90):
        raise AppError("Latitude out of range", details=[{"field": field_lat}])
    if not (-180 <= lng <= 180):
        raise AppError("Longitude out of range", details=[{"field": field_lng}])
    return lat, lng


def haversine_m(lat1: Decimal, lng1: Decimal, lat2: Decimal, lng2: Decimal) -> float:
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    dphi = math.radians(float(lat2 - lat1))
    dlmb = math.radians(float(lng2 - lng1))
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def geodesic_distance_m(lat1: Decimal, lng1: Decimal, lat2: Decimal, lng2: Decimal) -> float:
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    L = math.radians(float(lng2) - float(lng1))
    if abs(phi1 - phi2) < 1e-15 and abs(L) < 1e-15:
        return 0.0

    tan_u1 = (1.0 - _WGS84_F) * math.tan(phi1)
    tan_u2 = (1.0 - _WGS84_F) * math.tan(phi2)
    sin_u1, cos_u1 = tan_u1 / math.hypot(1.0, tan_u1), 1.0 / math.hypot(1.0, tan_u1)
    sin_u2, cos_u2 = tan_u2 / math.hypot(1.0, tan_u2), 1.0 / math.hypot(1.0, tan_u2)

    lam = L
    cos_sq_alpha = 1.0
    sin_sigma = cos_sigma = sigma = 0.0
    cos_2sigma_m = 0.0
    for _ in range(200):
        sin_lam, cos_lam = math.sin(lam), math.cos(lam)
        sin_sigma = math.hypot(
            cos_u2 * sin_lam,
            cos_u1 * sin_u2 - sin_u1 * cos_u2 * cos_lam,
        )
        if sin_sigma == 0.0:
            return 0.0
        cos_sigma = sin_u1 * sin_u2 + cos_u1 * cos_u2 * cos_lam
        sigma = math.atan2(sin_sigma, cos_sigma)
        sin_alpha = cos_u1 * cos_u2 * sin_lam / sin_sigma
        cos_sq_alpha = 1.0 - sin_alpha * sin_alpha
        if cos_sq_alpha != 0.0:
            cos_2sigma_m = cos_sigma - 2.0 * sin_u1 * sin_u2 / cos_sq_alpha
        else:
            cos_2sigma_m = 0.0
        c = _WGS84_F / 16.0 * cos_sq_alpha * (4.0 + _WGS84_F * (4.0 - 3.0 * cos_sq_alpha))
        lam_next = L + (1.0 - c) * _WGS84_F * sin_alpha * (
            sigma
            + c * sin_sigma * (cos_2sigma_m + c * cos_sigma * (-1.0 + 2.0 * cos_2sigma_m * cos_2sigma_m))
        )
        if abs(lam_next - lam) < 1e-12:
            lam = lam_next
            break
        lam = lam_next
    else:
        return haversine_m(lat1, lng1, lat2, lng2)

    u_sq = cos_sq_alpha * (_WGS84_A * _WGS84_A - _WGS84_B * _WGS84_B) / (_WGS84_B * _WGS84_B)
    a = 1.0 + u_sq / 16384.0 * (4096.0 + u_sq * (-768.0 + u_sq * (320.0 - 175.0 * u_sq)))
    b = u_sq / 1024.0 * (256.0 + u_sq * (-128.0 + u_sq * (74.0 - 47.0 * u_sq)))
    delta_sigma = (
        b
        * sin_sigma
        * (
            cos_2sigma_m
            + b
            / 4.0
            * (
                cos_sigma * (-1.0 + 2.0 * cos_2sigma_m * cos_2sigma_m)
                - b
                / 6.0
                * cos_2sigma_m
                * (-3.0 + 4.0 * sin_sigma * sin_sigma)
                * (-3.0 + 4.0 * cos_2sigma_m * cos_2sigma_m)
            )
        )
    )
    return _WGS84_B * a * (sigma - delta_sigma)


def is_stale(location_timestamp: datetime | None, max_age_seconds: int, now: datetime | None = None) -> bool:
    if location_timestamp is None:
        return True
    ts = location_timestamp if location_timestamp.tzinfo else location_timestamp.replace(tzinfo=UTC)
    now = now or datetime.now(UTC)
    return (now - ts).total_seconds() > max_age_seconds


def evaluate_geo(
    *,
    latitude: Decimal | None,
    longitude: Decimal | None,
    accuracy_m: Decimal | None,
    location_timestamp: datetime | None,
    site_latitude: Decimal,
    site_longitude: Decimal,
    geofence_radius_m: int,
    max_accuracy_m: int,
    max_age_seconds: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    flags: list[str] = []
    distance: float | None = None
    if latitude is None or longitude is None:
        flags.append(GeoFlag.GPS_MISSING.value)
        geo_status = GeoStatus.UNAVAILABLE
    else:
        validate_coordinates(latitude, longitude)
        distance = geodesic_distance_m(latitude, longitude, site_latitude, site_longitude)
        if accuracy_m is None:
            flags.append(GeoFlag.GPS_MISSING.value)
        elif float(accuracy_m) > max_accuracy_m:
            flags.append(GeoFlag.GPS_LOW_ACCURACY.value)
        if is_stale(location_timestamp, max_age_seconds, now):
            flags.append(GeoFlag.GPS_STALE.value)
        if distance > float(geofence_radius_m):
            flags.append(GeoFlag.OUTSIDE_GEOFENCE.value)
        geo_status = GeoStatus.WARNING if flags else GeoStatus.PASS
    return {
        "distance_m": round(distance, 1) if distance is not None else None,
        "flags": flags,
        "geo_status": geo_status.value,
    }
