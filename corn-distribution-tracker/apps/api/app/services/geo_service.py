"""Geolocation validation and geodesic distance.

Primary metric: Vincenty's inverse method on the WGS84 ellipsoid - a standard,
reviewed geodesic implementation (docs/architecture/GEO_PHOTO_EVIDENCE.md allows
"PostGIS geography or a reviewed geodesic implementation" where PostGIS is
unavailable). The spherical haversine on the IUGG mean Earth radius is kept as
the documented fallback for (nearly) antipodal point pairs, where Vincenty's
iteration does not converge; the spherical approximation carries a known bias
of up to ~0.5% at continental scales.
Accuracy tolerances are documented in organization settings; GPS/photo metadata
are indicators, never proof of authenticity.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.core.errors import AppError
from app.models.enums import GeoFlag, GeoStatus

EARTH_RADIUS_M = 6_371_008.8  # IUGG mean Earth radius (spherical fallback)

# WGS84 ellipsoid constants (Vincenty inverse).
_WGS84_A = 6_378_137.0  # semi-major axis, metres
_WGS84_F = 1.0 / 298.257223563  # flattening
_WGS84_B = _WGS84_A * (1.0 - _WGS84_F)  # semi-minor axis (≈ 6,356,752.314 m)


def validate_coordinates(
    latitude: Decimal, longitude: Decimal, *, field_lat: str = "latitude", field_lng: str = "longitude"
) -> tuple[Decimal, Decimal]:
    lat = Decimal(latitude)
    lng = Decimal(longitude)
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
    """WGS84 geodesic distance (Vincenty inverse, 1975), accurate to sub-metre.

    Falls back to the spherical haversine for (nearly) antipodal pairs, where
    the iterative solution is not guaranteed to converge.
    """
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    L = math.radians(float(lng2) - float(lng1))
    if abs(phi1 - phi2) < 1e-15 and abs(L) < 1e-15:
        return 0.0

    # Reduced latitudes (latitudes on the auxiliary sphere).
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
        if sin_sigma == 0.0:  # coincident points
            return 0.0
        cos_sigma = sin_u1 * sin_u2 + cos_u1 * cos_u2 * cos_lam
        sigma = math.atan2(sin_sigma, cos_sigma)
        sin_alpha = cos_u1 * cos_u2 * sin_lam / sin_sigma
        cos_sq_alpha = 1.0 - sin_alpha * sin_alpha
        if cos_sq_alpha != 0.0:
            cos_2sigma_m = cos_sigma - 2.0 * sin_u1 * sin_u2 / cos_sq_alpha
        else:
            cos_2sigma_m = 0.0  # equatorial line
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
        # Did not converge: near-antipodal pair. Use the documented fallback.
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
    """Return distance/flags/geo_status for a submission location against its site."""
    flags: list[str] = []
    distance: float | None = None
    if latitude is None or longitude is None:
        flags.append(GeoFlag.GPS_MISSING.value)
        status = GeoStatus.UNAVAILABLE
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
        status = GeoStatus.WARNING if flags else GeoStatus.PASS
    return {
        "distance_m": round(distance, 1) if distance is not None else None,
        "flags": flags,
        "geo_status": status.value,
    }
