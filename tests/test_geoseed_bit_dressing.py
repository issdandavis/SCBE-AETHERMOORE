from __future__ import annotations

import math

import pytest

from src.geoseed.bit_dressing import (
    CL60_COMPONENTS,
    bits_from_bytes,
    build_prime_abacus_layer,
    compose_dressed_bits,
    dress_bit,
    dress_bytes,
)


def test_bits_from_bytes_has_declared_bit_order() -> None:
    assert bits_from_bytes(b"\xa6") == (1, 0, 1, 0, 0, 1, 1, 0)
    assert bits_from_bytes(b"\xa6", bit_order="lsb") == (0, 1, 1, 0, 0, 1, 0, 1)
    with pytest.raises(ValueError, match="bit_order"):
        bits_from_bytes(b"\xa6", bit_order="sideways")  # type: ignore[arg-type]


def test_dress_bit_maps_to_tongue_prime_and_bounded_poincare_point() -> None:
    dressed = dress_bit(1, 5)

    assert dressed.schema_version == "geoseed_dressed_bit_v1"
    assert dressed.tongue_abbr == "DR"
    assert dressed.layer_prime == 13
    assert dressed.prime_residue == 6
    assert len(dressed.clifford_multivector) == CL60_COMPONENTS
    assert dressed.governance_stamp == "ALLOW"
    assert len(dressed.fingerprint) == 64

    radius = math.sqrt(sum(coord * coord for coord in dressed.poincare))
    assert 0.0 < radius < 1.0


def test_dressed_byte_composition_uses_prime_chunk_basis() -> None:
    dressed = dress_bytes(b"\xa6")
    composition = compose_dressed_bits(dressed)

    assert composition.bit_count == 8
    assert composition.one_count == 4
    assert composition.zero_count == 4
    assert composition.tongue_counts == {
        "KO": 2,
        "AV": 2,
        "RU": 1,
        "CA": 1,
        "UM": 1,
        "DR": 1,
    }
    assert composition.prime_one_counts == {
        "p2": 2,
        "p3": 0,
        "p5": 1,
        "p7": 0,
        "p11": 0,
        "p13": 1,
    }
    assert composition.prime_weighted_total == 22
    assert len(composition.fingerprint) == 64


def test_prime_abacus_layer_matches_polly_pad_row_contract() -> None:
    layer = build_prime_abacus_layer(dress_bytes(b"\xa6"))

    assert layer["id"] == "geoseed-prime"
    assert layer["name"] == "GeoSeed Prime Bit Chunks"
    rows = layer["rows"]
    assert isinstance(rows, list)
    assert rows[0] == {
        "id": "p2",
        "label": "prime 2 one-bits",
        "value": 2,
        "count": 2,
        "maxCount": 12,
    }
    assert sum(row["value"] * row["count"] for row in rows) == 22


def test_invalid_bits_and_empty_composition_fail_closed() -> None:
    with pytest.raises(ValueError, match="bit must"):
        dress_bit(2, 0)
    with pytest.raises(ValueError, match="index"):
        dress_bit(1, -1)
    with pytest.raises(ValueError, match="at least one"):
        compose_dressed_bits(())
