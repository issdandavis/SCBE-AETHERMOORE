from __future__ import annotations

import unittest

from held_context import EvidenceState, HeldContextLane, HeldContextPacket, LaneFlags, LaneKind, LaneRole
from sieve_codec import SieveError, compress_packet, decompress_packet, structural_pack, structural_unpack
from test_held_context import fixture_packet


class SieveCodecTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = fixture_packet().encode()

    def test_structural_round_trip(self) -> None:
        compact = structural_pack(self.raw)
        self.assertEqual(structural_unpack(compact), self.raw)

    def test_structural_stream_is_smaller_for_golden_packet(self) -> None:
        self.assertLess(len(structural_pack(self.raw)), len(self.raw))

    def test_wrapped_structural_round_trip(self) -> None:
        self.assertEqual(decompress_packet(compress_packet(self.raw, deflate=False)), self.raw)

    def test_wrapped_deflate_round_trip(self) -> None:
        self.assertEqual(decompress_packet(compress_packet(self.raw, deflate=True)), self.raw)

    def test_corruption_is_rejected(self) -> None:
        encoded = bytearray(compress_packet(self.raw))
        encoded[-1] ^= 1
        with self.assertRaises(SieveError):
            decompress_packet(bytes(encoded))

    def test_trailing_compressed_stream_is_rejected(self) -> None:
        with self.assertRaises(SieveError):
            decompress_packet(compress_packet(self.raw) + b"trailing")

    def test_provable_u16_token_view_is_stored_as_reference(self) -> None:
        payload = bytes(range(32))
        canonical = b"c" * 32
        source = b"s" * 32
        packet = HeldContextPacket(
            packet_id=b"p" * 16,
            generation=1,
            sequence_cutoff=0,
            token_budget=16,
            lanes=(
                HeldContextLane(
                    lane_id=1,
                    kind=LaneKind.ROOT,
                    evidence=EvidenceState.PRESENT,
                    role=LaneRole.OBSERVED,
                    flags=LaneFlags.EXACT_BYTES,
                    payload=payload,
                    canonical_value_id=canonical,
                    source_hash=source,
                ),
                HeldContextLane(
                    lane_id=2,
                    kind=LaneKind.LINGUISTIC,
                    evidence=EvidenceState.PRESENT,
                    role=LaneRole.DERIVED,
                    token_ids=tuple(
                        int.from_bytes(payload[index : index + 2], "little") for index in range(0, len(payload), 2)
                    ),
                    canonical_value_id=canonical,
                    source_hash=source,
                ),
            ),
        ).encode()
        compact = structural_pack(packet)
        self.assertEqual(structural_unpack(compact), packet)
        self.assertLess(len(compact), len(packet))


if __name__ == "__main__":
    unittest.main()
