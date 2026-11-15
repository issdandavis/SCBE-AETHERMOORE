from __future__ import annotations

import hashlib
import unittest

from held_context import (
    EvidenceState,
    HeldContextLane,
    HeldContextPacket,
    LaneFlags,
    LaneKind,
    LaneRole,
    NO_EXPIRY,
    PacketError,
    build_linguistic_lanes,
    decode_packet,
    select_visible_lanes,
)


def fixture_packet() -> HeldContextPacket:
    source = hashlib.sha256(b"source:teacher-loop-video").digest()
    canonical = hashlib.sha256(b"canonical:loops-and-arrays").digest()
    exact, tokens = build_linguistic_lanes(
        first_lane_id=10,
        text="Loop twice; then ABSTAIN.",
        tokenizer=lambda text: (ord(char) for char in text),
        canonical_value_id=canonical,
        source_hash=source,
    )
    geometry = HeldContextLane(
        lane_id=20,
        kind=LaneKind.GEOMETRY,
        evidence=EvidenceState.NEUTRAL,
        role=LaneRole.COMPUTED,
        flags=LaneFlags.COMPRESSIBLE,
        route_q1e6=(-500_000, 0, 500_000),
        payload=b"routing-only",
        canonical_value_id=canonical,
        source_hash=source,
    )
    abstain = HeldContextLane(
        lane_id=30,
        kind=LaneKind.TOOL,
        evidence=EvidenceState.ABSTAIN,
        role=LaneRole.CONTROL,
        expiry_sequence=150,
        canonical_value_id=hashlib.sha256(b"canonical:abstain").digest(),
        source_hash=source,
    )
    return HeldContextPacket(
        packet_id=bytes.fromhex("00112233445566778899aabbccddeeff"),
        generation=7,
        sequence_cutoff=100,
        token_budget=512,
        breath_q1e6=1_125_000,
        radius_q1e6=375_000,
        lanes=(exact, tokens, geometry, abstain),
    )


class HeldContextTests(unittest.TestCase):
    def test_round_trip_is_byte_exact(self) -> None:
        encoded = fixture_packet().encode()
        self.assertEqual(decode_packet(encoded).encode(), encoded)

    def test_trailing_bytes_are_rejected(self) -> None:
        with self.assertRaisesRegex(PacketError, "length"):
            decode_packet(fixture_packet().encode() + b"x")

    def test_header_corruption_is_rejected(self) -> None:
        raw = bytearray(fixture_packet().encode())
        raw[24] ^= 1
        with self.assertRaisesRegex(PacketError, "header CRC"):
            decode_packet(bytes(raw))

    def test_body_corruption_is_rejected(self) -> None:
        raw = bytearray(fixture_packet().encode())
        raw[-1] ^= 1
        with self.assertRaisesRegex(PacketError, "body CRC"):
            decode_packet(bytes(raw))

    def test_evidence_states_do_not_collapse(self) -> None:
        values = {int(state) for state in EvidenceState}
        self.assertEqual(values, {0, 1, 2, 3, 4})

    def test_unsorted_lanes_are_rejected(self) -> None:
        packet = fixture_packet()
        with self.assertRaisesRegex(PacketError, "ascending"):
            HeldContextPacket(
                packet_id=packet.packet_id,
                generation=packet.generation,
                sequence_cutoff=packet.sequence_cutoff,
                token_budget=packet.token_budget,
                lanes=tuple(reversed(packet.lanes)),
            ).encode()

    def test_expired_at_cutoff_is_rejected(self) -> None:
        lane = HeldContextLane(
            lane_id=1,
            kind=LaneKind.ROOT,
            evidence=EvidenceState.PRESENT,
            role=LaneRole.INDEPENDENT,
            expiry_sequence=9,
        )
        with self.assertRaisesRegex(PacketError, "expired"):
            HeldContextPacket(b"a" * 16, 0, 10, 1, lanes=(lane,)).encode()

    def test_visibility_uses_monotonic_sequence(self) -> None:
        packet = fixture_packet()
        self.assertEqual(len(select_visible_lanes(packet, current_sequence=150)), 4)
        self.assertEqual(len(select_visible_lanes(packet, current_sequence=151)), 3)
        with self.assertRaisesRegex(PacketError, "precedes"):
            select_visible_lanes(packet, current_sequence=99)

    def test_no_expiry_is_largest_u64(self) -> None:
        self.assertEqual(NO_EXPIRY, 0xFFFFFFFFFFFFFFFF)

    def test_radius_must_remain_inside_unit_ball(self) -> None:
        packet = fixture_packet()
        with self.assertRaisesRegex(PacketError, "unit ball"):
            HeldContextPacket(
                packet_id=packet.packet_id,
                generation=packet.generation,
                sequence_cutoff=packet.sequence_cutoff,
                token_budget=packet.token_budget,
                radius_q1e6=1_000_000,
                lanes=packet.lanes,
            ).encode()


if __name__ == "__main__":
    unittest.main()
