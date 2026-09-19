"""Tests for the six-lane bijective command transport."""

from __future__ import annotations

from dataclasses import replace
from itertools import combinations

import pytest

from python.scbe.semantic_opcode_vm import assemble
from src.fleet.bijective_frequency_transport import (
    BijectiveTransportError,
    TONGUE_ORDER,
    bundle_metrics,
    encode_payload,
    encode_program,
    prove_lane_token_bijections,
    recover_payload,
    recover_program,
)

PROGRAM = "; ".join(
    (
        "LOAD r0 4",
        "LOAD r1 6",
        "ADD r0 2",
        "COMPARE r0 6",
        "VERIFY",
        "STORE r0 1",
        "MEMORY_BIND 1",
        "HASH",
        "SEAL",
        "HALT",
    )
)


def _corrupt_lane(bundle, tongue: str):
    lanes = []
    for lane in bundle.lanes:
        if lane.tongue == tongue:
            changed = bytes((lane.symbols[0] ^ 0x01,)) + lane.symbols[1:]
            lane = replace(lane, symbols=changed)
        lanes.append(lane)
    return replace(bundle, lanes=tuple(lanes))


def test_ten_commands_round_trip_as_exact_opcode_tape() -> None:
    bundle = encode_program(PROGRAM)
    recovered = recover_program(bundle)

    assert bundle.command_count == 10
    assert recovered.program == assemble(PROGRAM)
    assert len(recovered.commands) == 10
    assert recovered.commands[0] == "LOAD r0 4"
    assert recovered.commands[-1] == "HALT"
    assert recovered.erased_lanes == ()
    assert recovered.used_parity is False


def test_every_single_lane_erasure_recovers_exact_program() -> None:
    bundle = encode_program(PROGRAM)

    for tongue in TONGUE_ORDER:
        recovered = recover_program(bundle, unavailable_lanes=(tongue,))
        assert recovered.program == assemble(PROGRAM)
        assert recovered.erased_lanes == (tongue,)
        assert recovered.used_parity is (tongue != TONGUE_ORDER[-1])


def test_single_corrupted_lane_is_detected_as_erasure_and_recovered() -> None:
    bundle = encode_program(PROGRAM)

    for tongue in TONGUE_ORDER:
        recovered = recover_program(_corrupt_lane(bundle, tongue))
        assert recovered.program == assemble(PROGRAM)
        assert recovered.erased_lanes == (tongue,)


def test_any_two_lane_erasures_are_outside_one_parity_contract() -> None:
    bundle = encode_program(PROGRAM)

    for unavailable in combinations(TONGUE_ORDER, 2):
        with pytest.raises(BijectiveTransportError):
            recover_program(bundle, unavailable_lanes=unavailable)


def test_manifest_change_is_rejected_before_reconstruction() -> None:
    bundle = encode_program(PROGRAM)
    altered = replace(bundle, packed_bytes=bundle.packed_bytes + 1)

    with pytest.raises(BijectiveTransportError, match="manifest checksum mismatch"):
        recover_program(altered)


def test_each_lane_round_trips_through_its_assigned_tongue() -> None:
    proof = prove_lane_token_bijections(encode_program(PROGRAM))

    assert tuple(proof) == TONGUE_ORDER
    assert all(proof.values())


def test_metrics_distinguish_condensation_from_redundancy() -> None:
    bundle = encode_program(PROGRAM)
    metrics = bundle_metrics(bundle)

    assert metrics["commands"] == 10
    assert metrics["wire_symbol_bytes"] == 6 * bundle.shard_size
    assert (
        metrics["coding_overhead_ratio"]
        == bundle.wire_symbol_bytes / bundle.packed_bytes
    )
    assert metrics["source_utf8_bytes"] == len(PROGRAM.encode("utf-8"))
    assert metrics["opcode_bytes"] == len(assemble(PROGRAM))


def test_repetition_compresses_but_noncompressing_mode_stays_identity() -> None:
    repeated = encode_payload(b"ABCD" * 100)
    identity = encode_payload(bytes(range(64)), allow_compression=False)

    assert repeated.codec == "zlib"
    assert repeated.packed_bytes < repeated.payload_bytes
    assert recover_payload(repeated).payload == b"ABCD" * 100
    assert identity.codec == "identity"
    assert recover_payload(identity).payload == bytes(range(64))


def test_empty_payload_and_unknown_lane_are_explicit() -> None:
    bundle = encode_payload(b"")

    assert recover_payload(bundle).payload == b""
    with pytest.raises(BijectiveTransportError, match="unknown unavailable lanes"):
        recover_payload(bundle, unavailable_lanes=("xx",))
