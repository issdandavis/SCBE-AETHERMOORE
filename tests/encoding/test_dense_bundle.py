"""Tests for src/encoding/dense_bundle.py."""

from __future__ import annotations

import json

import pytest

from src.encoding.dense_bundle import (
    LANE_BINARY_ANALYSIS,
    LANE_GOVERNANCE_INTENT,
    LANE_TEXT_DEFAULT,
    LANE_TRANSPORT_OPAQUE,
    DenseBundle,
    bundle_intent_profile,
    encode_for_route,
    equivalent_views,
    route_lane_for_bundle,
)

# ---------------------------------------------------------------------------
# Round-trip: every byte view decodes back to the original payload
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"a",
        b"hello",
        b"\x00\x01\x02\x03\xff\xfe\xfd",
        bytes(range(256)),
        b"SCBE-AETHERMOORE",
        "Sacred Tongues: KO/AV/RU/CA/UM/DR".encode("utf-8"),
    ],
)
@pytest.mark.parametrize("view", ["hex", "binary", "base64", "ternary"])
def test_byte_view_round_trip(payload: bytes, view: str) -> None:
    bundle = DenseBundle.from_bytes(payload)
    assert bundle.to_bytes(view) == payload, f"{view!r} view did not round-trip"


def test_text_round_trip_unicode() -> None:
    text = "phi: φ — Sacred Tongues 🌀 mix"
    bundle = DenseBundle.from_text(text)
    assert bundle.to_text("hex") == text
    assert bundle.to_text("binary") == text
    assert bundle.to_text("base64") == text
    assert bundle.to_text("ternary") == text


def test_empty_payload_is_well_defined() -> None:
    bundle = DenseBundle.from_bytes(b"")
    assert bundle.byte_length == 0
    assert bundle.binary == ""
    assert bundle.hex == ""
    assert bundle.base64 == ""
    assert bundle.intent == ()
    for view in ("hex", "binary", "base64", "ternary"):
        assert bundle.to_bytes(view) == b""


# ---------------------------------------------------------------------------
# Encoding shape
# ---------------------------------------------------------------------------


def test_binary_view_is_eight_bits_per_byte() -> None:
    bundle = DenseBundle.from_bytes(b"\x00\xff\xa5")
    assert bundle.binary == "00000000" "11111111" "10100101"


def test_hex_view_matches_bytes_hex() -> None:
    payload = b"\xde\xad\xbe\xef"
    assert DenseBundle.from_bytes(payload).hex == payload.hex()


# ---------------------------------------------------------------------------
# Intent overlay
# ---------------------------------------------------------------------------


def test_intent_overlay_polarity() -> None:
    bundle = DenseBundle.from_bytes(b"\x00\x41\xff")
    # 0x00 -> ZERO (0), 0x41 (low ASCII 'A') -> POS (+1), 0xff -> NEG (-1)
    assert bundle.intent == (0, 1, -1)


def test_intent_profile_sums_to_one() -> None:
    bundle = DenseBundle.from_bytes(bytes(range(256)))
    profile = bundle_intent_profile(bundle)
    assert profile["neg"] + profile["zero"] + profile["pos"] == pytest.approx(1.0)
    # 1 zero byte, 127 low-ASCII (POS), 128 high-bit (NEG)
    assert profile["zero"] == pytest.approx(1 / 256)
    assert profile["pos"] == pytest.approx(127 / 256)
    assert profile["neg"] == pytest.approx(128 / 256)


def test_intent_profile_empty() -> None:
    bundle = DenseBundle.from_bytes(b"")
    assert bundle_intent_profile(bundle) == {"neg": 0.0, "zero": 0.0, "pos": 0.0}


# ---------------------------------------------------------------------------
# JSON serialization
# ---------------------------------------------------------------------------


def test_to_dict_round_trip() -> None:
    bundle = DenseBundle.from_bytes(b"hello world")
    serialized = json.dumps(bundle.to_dict())
    restored = DenseBundle.from_dict(json.loads(serialized))
    assert restored == bundle
    assert restored.to_bytes("hex") == b"hello world"


# ---------------------------------------------------------------------------
# Bus routing
# ---------------------------------------------------------------------------


def test_route_lane_for_bundle_dispatch() -> None:
    assert route_lane_for_bundle("hex") == LANE_BINARY_ANALYSIS
    assert route_lane_for_bundle("binary") == LANE_BINARY_ANALYSIS
    assert route_lane_for_bundle("ternary") == LANE_GOVERNANCE_INTENT
    assert route_lane_for_bundle("base64") == LANE_TRANSPORT_OPAQUE
    assert route_lane_for_bundle("text") == LANE_TEXT_DEFAULT
    assert route_lane_for_bundle("unknown_view") == LANE_TEXT_DEFAULT


def test_encode_for_route_returns_bundle_and_lane() -> None:
    bundle, lane = encode_for_route("hello", view="ternary")
    assert isinstance(bundle, DenseBundle)
    assert lane == LANE_GOVERNANCE_INTENT
    assert bundle.to_text("ternary") == "hello"

    bundle_b, lane_b = encode_for_route(b"\x00\xff", view="hex")
    assert lane_b == LANE_BINARY_ANALYSIS
    assert bundle_b.to_bytes("hex") == b"\x00\xff"


# ---------------------------------------------------------------------------
# equivalent_views helper
# ---------------------------------------------------------------------------


def test_equivalent_views_all_match() -> None:
    payload = b"the quick brown fox"
    a, b, c, d = equivalent_views(payload)
    assert a == b == c == d == payload


def test_equivalent_views_accepts_int_sequence() -> None:
    payload_ints = [0, 1, 2, 255]
    a, b, c, d = equivalent_views(payload_ints)
    assert a == b == c == d == bytes(payload_ints)


# ---------------------------------------------------------------------------
# Density observability
# ---------------------------------------------------------------------------


def test_density_ratio_sane() -> None:
    bundle = DenseBundle.from_bytes(b"a" * 100)
    # binary = 800 chars, hex = 200, base64 = ~136, ternary varies
    ratio = bundle.density_ratio()
    assert ratio > 10  # at minimum the binary view alone is 8x
    assert ratio < 100  # sanity ceiling


def test_density_ratio_empty_is_zero() -> None:
    assert DenseBundle.from_bytes(b"").density_ratio() == 0.0


# ---------------------------------------------------------------------------
# Bad input
# ---------------------------------------------------------------------------


def test_to_bytes_unknown_view_raises() -> None:
    bundle = DenseBundle.from_bytes(b"x")
    with pytest.raises(ValueError, match="unknown view"):
        bundle.to_bytes("invalid_view")


def test_corrupted_binary_view_raises() -> None:
    # Manually construct a bundle with a binary length that's not a multiple of 8.
    bundle = DenseBundle(byte_length=1, binary="0101", hex="55", base64="VQ==", ternary="0", intent=(1,))
    with pytest.raises(ValueError, match="multiple of 8"):
        bundle.to_bytes("binary")
