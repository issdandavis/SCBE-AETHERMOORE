"""Tests for geo_fenced_seal — policy-layer geo unseal on sealed packets."""

from __future__ import annotations

import pytest

from src.crypto.geo_fenced_seal import (
    GeoFenceViolation,
    haversine_meters,
    seal_with_geo_fence,
    unseal_with_geo_check,
)
from src.crypto.sealed_memory_packets import unseal_memory_packet


PORT_ANGELES = {"lat": 48.1181, "lon": -123.4307}
SEQUIM = {"lat": 48.0792, "lon": -123.1027}             # ~25 km east
SEATTLE = {"lat": 47.6062, "lon": -122.3321}            # ~120 km east-southeast
MOSCOW = {"lat": 55.7558, "lon": 37.6173}               # ~8500 km
SECRET = b"k" * 32
PAYLOAD = b"agent state v1: deploy=true, run=42"


def test_haversine_known_pairs() -> None:
    # Port Angeles → Sequim ≈ 24 km, ±1 km
    d = haversine_meters(
        PORT_ANGELES["lat"], PORT_ANGELES["lon"], SEQUIM["lat"], SEQUIM["lon"]
    )
    assert 23_000 < d < 26_000
    # Self-distance is zero
    assert haversine_meters(48.0, -123.0, 48.0, -123.0) == pytest.approx(0.0, abs=1e-6)


def test_seal_unseal_inside_fence() -> None:
    pkt = seal_with_geo_fence(
        SECRET, PAYLOAD,
        geo_fence={**PORT_ANGELES, "radius_m": 5_000},
    )
    out = unseal_with_geo_check(
        SECRET, pkt, current_location=PORT_ANGELES,
    )
    assert out["payload"] == PAYLOAD
    assert out["geo_fence_check"]["passed"] is True
    assert out["geo_fence_check"]["distance_m"] < 1.0


def test_unseal_outside_fence_raises() -> None:
    pkt = seal_with_geo_fence(
        SECRET, PAYLOAD,
        geo_fence={**PORT_ANGELES, "radius_m": 5_000},
    )
    # Sequim is ~25 km away — well outside a 5 km fence.
    with pytest.raises(GeoFenceViolation) as exc_info:
        unseal_with_geo_check(SECRET, pkt, current_location=SEQUIM)
    assert "fence radius" in str(exc_info.value)


def test_far_away_violates() -> None:
    pkt = seal_with_geo_fence(
        SECRET, PAYLOAD,
        geo_fence={**PORT_ANGELES, "radius_m": 1_000_000},  # 1000 km radius
    )
    # Moscow is way outside any sane fence around Port Angeles.
    with pytest.raises(GeoFenceViolation):
        unseal_with_geo_check(SECRET, pkt, current_location=MOSCOW)


def test_packet_without_fence_rejects_geo_unseal() -> None:
    # Seal without geo_fence metadata — must not silently bypass the policy.
    pkt = seal_with_geo_fence(
        SECRET, PAYLOAD, geo_fence={**PORT_ANGELES, "radius_m": 5_000}
    )
    # Manually strip the fence to simulate a downgrade attempt.
    pkt["metadata"] = {k: v for k, v in pkt["metadata"].items() if k != "geo_fence"}
    with pytest.raises(ValueError):
        unseal_with_geo_check(SECRET, pkt, current_location=PORT_ANGELES)


def test_tampered_fence_breaks_aead() -> None:
    # Bind to Port Angeles, attacker tries to widen the fence to cover Moscow.
    pkt = seal_with_geo_fence(
        SECRET, PAYLOAD,
        geo_fence={**PORT_ANGELES, "radius_m": 1_000},
    )
    pkt["metadata"]["geo_fence"]["radius_m"] = 100_000_000  # global
    # The metadata is AAD-bound, so the AEAD verification fails before policy
    # even runs. We expect *some* exception from the unseal pipeline.
    with pytest.raises(Exception):
        unseal_memory_packet(SECRET, pkt)


def test_invalid_fence_inputs() -> None:
    with pytest.raises(ValueError):
        seal_with_geo_fence(SECRET, PAYLOAD, geo_fence={"lat": 91.0, "lon": 0.0, "radius_m": 1.0})
    with pytest.raises(ValueError):
        seal_with_geo_fence(SECRET, PAYLOAD, geo_fence={"lat": 0.0, "lon": 200.0, "radius_m": 1.0})
    with pytest.raises(ValueError):
        seal_with_geo_fence(SECRET, PAYLOAD, geo_fence={"lat": 0.0, "lon": 0.0, "radius_m": -10})


def test_metadata_geo_fence_collision_rejected() -> None:
    # Caller cannot smuggle a geo_fence in via metadata — must use the kwarg.
    with pytest.raises(ValueError):
        seal_with_geo_fence(
            SECRET, PAYLOAD,
            geo_fence={**PORT_ANGELES, "radius_m": 100},
            metadata={"geo_fence": {"lat": 0.0, "lon": 0.0, "radius_m": 100}},
        )
