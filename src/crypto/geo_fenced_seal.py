"""Geo-fenced unseal policy layer on top of sealed_memory_packets.

What this is — *and is not*
---------------------------
This module adds a **policy check** that refuses to unseal a packet unless the
caller can prove they are within a configured radius of a target lat/lon at
unseal time. The cryptography is unchanged: the underlying RWP v3 envelope is
a normal AEAD seal. Geo coordinates are written into the packet's
`metadata.geo_fence`, which is *AAD-bound* by `seal_memory_packet`, so
tampering with the fence values fails the AEAD verification.

What this gives you:
  * tamper-evident geographic policy: an attacker can't quietly change the
    fence to "anywhere on earth" without breaking the seal.
  * an at-rest unseal lockout: a sealed packet copied off-base won't open even
    if the secret is exfiltrated, *as long as the unsealing program enforces
    the fence*.

What this does NOT give you:
  * crypto-strength location binding. The seal itself is not derived from
    GPS. A determined attacker who controls the unsealing program can patch
    out the fence check. Treat this as defense-in-depth, not as a key
    derivation function.
  * spoof resistance. GPS itself is spoofable. For a real defense deployment,
    pair this with a hardware GNSS receiver that signs its fixes.

Distance math
-------------
Haversine on a spherical earth (R = 6 371 008.8 m). Accurate to <0.5% at the
ranges where geo-fences are useful (meters to thousands of km).
"""

from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Optional

from .sealed_memory_packets import (
    Payload,
    Secret,
    seal_memory_packet,
    unseal_memory_packet,
)

EARTH_RADIUS_M = 6_371_008.8


# ---------------------------------------------------------------------------
#  Distance
# ---------------------------------------------------------------------------

def haversine_meters(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    """Great-circle distance between two (lat, lon) points in meters."""
    phi_a = math.radians(lat_a)
    phi_b = math.radians(lat_b)
    d_phi = math.radians(lat_b - lat_a)
    d_lam = math.radians(lon_b - lon_a)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi_a) * math.cos(phi_b) * math.sin(d_lam / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_M * c


def _validate_fence(fence: Mapping[str, Any]) -> Dict[str, float]:
    try:
        lat = float(fence["lat"])
        lon = float(fence["lon"])
        radius_m = float(fence["radius_m"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("geo_fence must include numeric lat, lon, radius_m") from exc
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"lat out of range: {lat}")
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"lon out of range: {lon}")
    if radius_m <= 0 or not math.isfinite(radius_m):
        raise ValueError(f"radius_m must be positive and finite: {radius_m}")
    return {"lat": lat, "lon": lon, "radius_m": radius_m}


# ---------------------------------------------------------------------------
#  Seal / unseal with geo policy
# ---------------------------------------------------------------------------

class GeoFenceViolation(PermissionError):
    """Raised when an unseal attempt is outside the configured fence."""


def seal_with_geo_fence(
    secret: Secret,
    payload: Payload,
    *,
    geo_fence: Mapping[str, Any],
    label: str = "geo_memory",
    tongue: str = "ko",
    metadata: Optional[Mapping[str, Any]] = None,
    enable_pqc: bool = False,
) -> Dict[str, Any]:
    """Seal `payload` and bind it to a (lat, lon, radius_m) fence.

    The fence is stored under `metadata.geo_fence`. Because metadata is
    AAD-bound by the sealed-memory-packet module, any tampering with the
    fence fields fails AEAD verification.
    """
    fence = _validate_fence(geo_fence)
    extra = dict(metadata or {})
    if "geo_fence" in extra:
        raise ValueError("metadata.geo_fence is reserved; pass geo_fence kwarg instead")
    extra["geo_fence"] = fence
    return seal_memory_packet(
        secret,
        payload,
        tongue=tongue,
        label=label,
        metadata=extra,
        enable_pqc=enable_pqc,
    )


def unseal_with_geo_check(
    secret: Secret,
    packet: Mapping[str, Any],
    *,
    current_location: Mapping[str, Any],
    enable_pqc: bool = False,
) -> Dict[str, Any]:
    """Unseal a geo-fenced packet and enforce the fence.

    Raises GeoFenceViolation if the caller's current_location is outside the
    fence. Raises ValueError if the packet is missing a fence — geo-fenced
    unseal must not silently fall through to a normal unseal.
    """
    fence_raw = (packet.get("metadata") or {}).get("geo_fence")
    if not fence_raw:
        raise ValueError("packet has no geo_fence metadata")
    fence = _validate_fence(fence_raw)

    try:
        cur_lat = float(current_location["lat"])
        cur_lon = float(current_location["lon"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("current_location must include numeric lat, lon") from exc

    distance_m = haversine_meters(fence["lat"], fence["lon"], cur_lat, cur_lon)
    if distance_m > fence["radius_m"]:
        raise GeoFenceViolation(
            f"current location is {distance_m:.1f} m from fence center; "
            f"fence radius is {fence['radius_m']:.1f} m"
        )

    result = unseal_memory_packet(secret, packet, enable_pqc=enable_pqc)
    result["geo_fence_check"] = {
        "fence": fence,
        "current": {"lat": cur_lat, "lon": cur_lon},
        "distance_m": distance_m,
        "passed": True,
    }
    return result


__all__ = [
    "haversine_meters",
    "GeoFenceViolation",
    "seal_with_geo_fence",
    "unseal_with_geo_check",
]
