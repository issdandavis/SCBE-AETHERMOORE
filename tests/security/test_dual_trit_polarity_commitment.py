from __future__ import annotations

import random

import pytest

from src.crypto.dual_trit_polarity_commitment import (
    commit_dual_trit_field,
    decode_dual_trit_field,
    direct_shake256_commitment,
    dual_trit_root,
    encode_dual_trit_field,
    polarity_cell,
)


def _bit_distance(left: bytes, right: bytes) -> int:
    return sum((a ^ b).bit_count() for a, b in zip(left, right))


def test_all_byte_cells_are_unique_and_round_trip() -> None:
    cells = [polarity_cell(byte) for byte in range(256)]

    assert len({cell.positive_rail for cell in cells}) == 256
    assert {cell.shell for cell in cells} == set(range(1, 129))
    assert sum(cell.polarity < 0 for cell in cells) == 128
    assert sum(cell.polarity > 0 for cell in cells) == 128
    for byte, cell in enumerate(cells):
        opposite = polarity_cell(255 - byte)
        assert opposite.centered == -cell.centered
        assert opposite.positive_rail == cell.negative_rail
        assert cell.negative_rail == tuple(-value for value in cell.positive_rail)
        assert decode_dual_trit_field(encode_dual_trit_field(bytes((byte,)))) == bytes(
            (byte,)
        )


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"\x00",
        b"\xff",
        bytes(range(256)),
        "dual trit polarity \u03c6".encode(),
    ],
)
def test_field_round_trip_and_commitment_verification(payload: bytes) -> None:
    field = encode_dual_trit_field(payload)
    commitment = commit_dual_trit_field(payload, context=b"unit-test")

    assert decode_dual_trit_field(field) == payload
    assert dual_trit_root(payload, context=b"unit-test") == commitment.center
    assert commitment.verify(payload, context=b"unit-test")
    assert not commitment.verify(payload + b"!", context=b"unit-test")
    assert not commitment.verify(payload, context=b"other-context")


def test_malformed_or_non_inverse_fields_fail_closed() -> None:
    field = bytearray(encode_dual_trit_field(b"A"))
    field[-1] = 1 if field[-1] != 1 else 2
    with pytest.raises(ValueError, match="inverse"):
        decode_dual_trit_field(bytes(field))

    truncated = encode_dual_trit_field(b"AB")[:-1]
    with pytest.raises(ValueError, match="length"):
        decode_dual_trit_field(truncated)


def test_single_bit_changes_have_sha3_like_avalanche() -> None:
    rng = random.Random(20260919)
    direct_distances = []
    dual_distances = []
    output_bits = 64 * 8

    for _ in range(128):
        payload = bytearray(rng.randbytes(64))
        byte_index = rng.randrange(len(payload))
        bit_index = rng.randrange(8)
        changed = bytearray(payload)
        changed[byte_index] ^= 1 << bit_index

        direct_distances.append(
            _bit_distance(
                direct_shake256_commitment(bytes(payload)),
                direct_shake256_commitment(bytes(changed)),
            )
            / output_bits
        )
        dual_distances.append(
            _bit_distance(
                commit_dual_trit_field(bytes(payload)).root,
                commit_dual_trit_field(bytes(changed)).root,
            )
            / output_bits
        )

    direct_mean = sum(direct_distances) / len(direct_distances)
    dual_mean = sum(dual_distances) / len(dual_distances)
    assert 0.45 <= direct_mean <= 0.55
    assert 0.45 <= dual_mean <= 0.55
    assert abs(direct_mean - dual_mean) <= 0.03


def test_small_domain_has_no_observed_collisions() -> None:
    direct = set()
    dual_root = set()
    dual = set()
    for value in range(4096):
        payload = value.to_bytes(2, "big")
        direct.add(direct_shake256_commitment(payload))
        dual_root.add(dual_trit_root(payload))
        dual.add(commit_dual_trit_field(payload).root)

    assert len(direct) == 4096
    assert len(dual_root) == 4096
    assert len(dual) == 4096


def test_output_size_is_bounded_to_reviewed_range() -> None:
    for invalid in (0, 16, 31, 65, 1024):
        with pytest.raises(ValueError, match="output_bytes"):
            commit_dual_trit_field(b"test", output_bytes=invalid)
        with pytest.raises(ValueError, match="output_bytes"):
            dual_trit_root(b"test", output_bytes=invalid)
