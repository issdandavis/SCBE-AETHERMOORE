"""Geographically-aware GeoSeal helpers for SCBE applications.

This module provides a small reusable API for:

- Optional geolocation-aware ring gating (core/outer/blocked).
- Geodesic distance helpers and geoid derivation.
- Lightweight location inference from a public IP endpoint.
- Packaging-friendly, side-effect-light building blocks that can be imported by
  scripts and services.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
import urllib.request
from dataclasses import dataclass
from typing import Dict, Tuple


DEFAULT_CORE_MAX = 0.30
DEFAULT_OUTER_MAX = 0.70


@dataclass(frozen=True)
class Geolocation:
    """Normalized user geolocation."""

    latitude: float
    longitude: float
    source: str = "manual"
    accuracy_m: float | None = None
    timestamp_ms: int | None = None

    def as_tuple(self) -> Tuple[float, float]:
        return (self.latitude, self.longitude)


@dataclass(frozen=True)
class GeoSealLocationDecision:
    """Decision record returned by :func:`evaluate_geoseal_location`."""

    ring: str
    risk_radius: float
    distance_km: float | None
    trust_score: float
    geoid: str
    status: str
    reason: str


def _coerce_lat_lon(value: float) -> float:
    if not isinstance(value, (int, float)):
        raise TypeError("latitude/longitude must be numeric")
    return float(value)


def _normalize_lat_lon(latitude: float, longitude: float) -> Tuple[float, float]:
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError("latitude must be in [-90, 90]")
    # Keep longitude in [-180, 180)
    lon = ((longitude + 180.0) % 360.0) - 180.0
    return float(latitude), float(lon)


def haversine_km(
    lat_a: float,
    lon_a: float,
    lat_b: float,
    lon_b: float,
    radius_km: float = 6371.0,
) -> float:
    """Compute geodesic distance between two coordinates in kilometers."""
    lat1, lon1 = map(math.radians, _normalize_lat_lon(lat_a, lon_a))
    lat2, lon2 = map(math.radians, _normalize_lat_lon(lat_b, lon_b))

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    hav = math.sin(dlat / 2.0) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
    return radius_km * 2.0 * math.asin(min(1.0, math.sqrt(hav)))


def geoid(lat: float, lon: float, grid: float = 0.01) -> str:
    """Return a deterministic geospatial identity string for audit/logging."""
    lat_q = round(_coerce_lat_lon(lat), int(max(0, -math.floor(math.log10(grid))) ) )
    lon_q = round(_coerce_lat_lon(lon), int(max(0, -math.floor(math.log10(grid))) ) )
    payload = f"{lat_q:.5f}|{lon_q:.5f}|{grid:.5f}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def infer_location_from_ip(ipapi_url: str = "https://ipapi.co/json/") -> Geolocation:
    """Fetch geolocation from a public endpoint (best-effort only).

    The default endpoint is free and may rate limit; callers should treat this as
    optional infrastructure (not a trust root).
    """
    req = urllib.request.Request(ipapi_url, headers={"User-Agent": "SCBE-Geoseal-Location/1.0"})
    with urllib.request.urlopen(req, timeout=4) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    if "latitude" not in payload or "longitude" not in payload:
        raise ValueError("missing latitude/longitude in location payload")

    lat = _coerce_lat_lon(payload["latitude"])
    lon = _coerce_lat_lon(payload["longitude"])
    lat, lon = _normalize_lat_lon(lat, lon)
    accuracy = payload.get("accuracy")
    return Geolocation(
        latitude=lat,
        longitude=lon,
        source=str(payload.get("ip", "ipapi")),
        accuracy_m=float(accuracy) if accuracy is not None else None,
        timestamp_ms=int(time.time() * 1000),
    )


def evaluate_geoseal_location(
    *,
    user_latitude: float | None,
    user_longitude: float | None,
    reference_latitude: float | None,
    reference_longitude: float | None,
    trusted_radius_km: float,
    core_radius_km: float = 5.0,
    outer_radius_km: float = 80.0,
    core_max: float = DEFAULT_CORE_MAX,
    outer_max: float = DEFAULT_OUTER_MAX,
) -> GeoSealLocationDecision:
    """Return a GeoSeal-like ring decision with location-based scoring.

    The location component contributes a normalized distance score:
      - 0.0 at the center reference
      - 1.0 at ``trusted_radius_km``
      - values beyond trusted_radius_km saturate at 1.0
    """
    if user_latitude is None or user_longitude is None:
        return GeoSealLocationDecision(
            ring="blocked",
            risk_radius=1.0,
            distance_km=None,
            trust_score=0.0,
            geoid=geoid(0.0, 0.0),
            status="missing_location",
            reason="user location not provided",
        )

    if reference_latitude is None or reference_longitude is None:
        # Distance-only fallback
        distance_km = None
        distance_score = 0.5
    else:
        distance_km = haversine_km(
            _coerce_lat_lon(user_latitude),
            _coerce_lat_lon(user_longitude),
            _coerce_lat_lon(reference_latitude),
            _coerce_lat_lon(reference_longitude),
        )
        distance_score = min(1.0, distance_km / max(1e-9, trusted_radius_km))

    # Optional tier-specific compression for near/far behavior.
    # Inside core radius: lower risk profile.
    if distance_km is not None and distance_km <= core_radius_km:
        distance_score *= 0.35
    elif distance_km is not None and distance_km <= outer_radius_km:
        distance_score *= 0.7

    # Combine distance score with a bounded trust radius.
    risk_radius = min(1.0, 0.85 * distance_score + 0.15 * (0.0 if distance_km is None else distance_km / max(outer_radius_km, 1.0)))
    trust = round(1.0 - risk_radius, 4)

    if risk_radius <= core_max:
        ring = "core"
        status = "geo_within_core"
    elif risk_radius <= outer_max:
        ring = "outer"
        status = "geo_within_outer"
    else:
        ring = "blocked"
        status = "geo_out_of_bounds"

    return GeoSealLocationDecision(
        ring=ring,
        risk_radius=round(risk_radius, 6),
        distance_km=None if distance_km is None else round(distance_km, 6),
        trust_score=trust,
        geoid=geoid(_coerce_lat_lon(user_latitude), _coerce_lat_lon(user_longitude)),
        status=status,
        reason=f"distance_km={distance_km if distance_km is None else round(distance_km, 4)}",
    )


def decision_to_metadata(decision: GeoSealLocationDecision) -> Dict[str, object]:
    """Convert a decision to a JSON-friendly payload."""
    return decision.__dict__
