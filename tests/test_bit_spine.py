"""Tests for the byte-exact binary/hex/trit spine and binary Turing core."""

from __future__ import annotations

import pytest

from python.scbe.bit_spine import (
    BitSpine,
    BitSpineError,
    bf_to_ops,
    binary_increment_machine,
    bits_to_bytes,
    bytes_to_bits,
    bytes_to_trits,
    ops_to_bf,
    pack_ops,
    run_bf,
    trits_to_bytes,
    unpack_ops,
)


def test_binary_hex_trit_projections_round_trip_bit_exact() -> None:
    payload = bytes(range(256))
    spine = BitSpine(payload)

    assert BitSpine.from_bits(spine.bits()).data == payload
    assert BitSpine.from_hex(spine.hex()).data == payload
    assert BitSpine.from_trits(spine.trits()).data == payload
    assert trits_to_bytes(bytes_to_trits(payload)) == payload
    assert bits_to_bytes(bytes_to_bits(payload)) == payload


def test_trit_projection_rejects_invalid_unused_base3_cells() -> None:
    # Six raw ternary 2s represent 728, outside byte range.
    with pytest.raises(BitSpineError, match="invalid byte trit cell"):
        trits_to_bytes([1, 1, 1, 1, 1, 1])


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("0", "1"),
        ("1", "10"),
        ("10", "11"),
        ("11", "100"),
        ("1011", "1100"),
        ("1111", "10000"),
    ],
)
def test_binary_turing_increment_machine(before: str, after: str) -> None:
    result = binary_increment_machine().run(before)
    assert result["state"] == "HALT"
    assert result["bits"] == after


def test_spine_opcode_tape_packs_as_3_bit_binary_and_round_trips() -> None:
    ops = bf_to_ops("++>+.<")
    blob = pack_ops(ops)

    assert blob.startswith(b"BSPN")
    assert unpack_ops(blob) == ops
    assert ops_to_bf(ops) == "++>+.<"


def test_spine_opcode_runtime_executes_turing_complete_core_slice() -> None:
    # Add 65 to cell zero and output "A".
    assert run_bf("+" * 65 + ".") == b"A"


def test_spine_program_hash_detects_tamper() -> None:
    blob = bytearray(pack_ops(bf_to_ops("+.")))
    blob[-1] ^= 0x01

    with pytest.raises(BitSpineError, match="hash mismatch"):
        unpack_ops(bytes(blob))
