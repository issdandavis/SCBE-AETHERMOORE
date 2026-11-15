"""HCTX-Sieve v1: reversible structural preconditioning for context packets.

The codec removes representation redundancy already implied by the canonical
packet: repeated hashes become dictionary references, monotonic lane IDs become
deltas, route coordinates and token IDs become signed deltas, and fixed headers
become varints.  Optional DEFLATE then compresses the compact stream.  This is a
packet-family codec, not a claim of a new general-purpose entropy bound.
"""

from __future__ import annotations

import struct
import zlib

from held_context import (
    EvidenceState,
    HeldContextLane,
    HeldContextPacket,
    LaneFlags,
    LaneKind,
    LaneRole,
    PacketError,
    ZERO_HASH,
    decode_packet,
)

SIEVE_MAGIC = b"HCS1"
SIEVE_VERSION = 1
MODE_STRUCTURAL = 0
MODE_DEFLATE = 1
WRAPPER = struct.Struct("<4sBBHIIII")
MAX_TRANSFORMED_LEN = 32 * 1024 * 1024


class SieveError(ValueError):
    pass


def _put_varint(output: bytearray, value: int) -> None:
    if isinstance(value, bool) or not 0 <= value <= 0xFFFFFFFFFFFFFFFF:
        raise SieveError("varint must fit u64")
    while value >= 0x80:
        output.append((value & 0x7F) | 0x80)
        value >>= 7
    output.append(value)


def _get_varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    for shift in range(0, 70, 7):
        if offset >= len(data):
            raise SieveError("truncated varint")
        byte = data[offset]
        offset += 1
        if shift == 63 and byte > 1:
            raise SieveError("varint exceeds u64")
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, offset
    raise SieveError("varint exceeds ten bytes")


def _zigzag(value: int) -> int:
    if not -(1 << 63) <= value < (1 << 63):
        raise SieveError("signed delta must fit i64")
    return (value << 1) ^ (value >> 63)


def _unzigzag(value: int) -> int:
    return (value >> 1) ^ -(value & 1)


def structural_pack(raw_packet: bytes) -> bytes:
    packet = decode_packet(raw_packet)
    hashes = [ZERO_HASH]
    hash_indexes = {ZERO_HASH: 0}
    for lane in packet.lanes:
        for value in (lane.canonical_value_id, lane.source_hash):
            if value not in hash_indexes:
                hash_indexes[value] = len(hashes)
                hashes.append(value)

    output = bytearray(b"SV3")
    output.extend(packet.packet_id)
    output.append(packet.flags)
    _put_varint(output, packet.generation)
    _put_varint(output, packet.sequence_cutoff)
    _put_varint(output, packet.token_budget)
    _put_varint(output, _zigzag(packet.breath_q1e6))
    _put_varint(output, packet.radius_q1e6)
    _put_varint(output, len(packet.lanes))
    _put_varint(output, len(hashes))
    for value in hashes:
        output.extend(value)

    previous_lane_id = 0
    for lane_index, lane in enumerate(packet.lanes):
        _put_varint(output, lane.lane_id - previous_lane_id)
        previous_lane_id = lane.lane_id
        meta = int(lane.kind) | (int(lane.evidence) << 3) | (int(lane.role) << 6) | (int(lane.flags) << 9)
        _put_varint(output, meta)
        expiry_delta = (
            0 if lane.expiry_sequence == 0xFFFFFFFFFFFFFFFF else lane.expiry_sequence - packet.sequence_cutoff + 1
        )
        _put_varint(output, expiry_delta)
        _put_varint(output, hash_indexes[lane.canonical_value_id])
        _put_varint(output, hash_indexes[lane.source_hash])

        _put_varint(output, len(lane.route_q1e6))
        previous_coordinate = 0
        for coordinate in lane.route_q1e6:
            _put_varint(output, _zigzag(coordinate - previous_coordinate))
            previous_coordinate = coordinate

        token_reference: tuple[int, int] | None = None
        if lane.role == LaneRole.DERIVED and lane.token_ids:
            for prior_index, prior in enumerate(packet.lanes[:lane_index]):
                if not (
                    prior.flags & LaneFlags.EXACT_BYTES
                    and prior.canonical_value_id == lane.canonical_value_id
                    and prior.source_hash == lane.source_hash
                ):
                    continue
                candidates = (
                    (1, tuple(prior.payload)),
                    (
                        2,
                        (
                            tuple(
                                int.from_bytes(prior.payload[pos : pos + 2], "little")
                                for pos in range(0, len(prior.payload), 2)
                            )
                            if len(prior.payload) % 2 == 0
                            else ()
                        ),
                    ),
                    (
                        3,
                        (
                            tuple(
                                int.from_bytes(prior.payload[pos : pos + 4], "little")
                                for pos in range(0, len(prior.payload), 4)
                            )
                            if len(prior.payload) % 4 == 0
                            else ()
                        ),
                    ),
                )
                for mode, candidate in candidates:
                    if candidate == lane.token_ids:
                        token_reference = (prior_index, mode)
                        break
                if token_reference is not None:
                    break
        if token_reference is None:
            _put_varint(output, len(lane.token_ids) << 2)
            previous_token = 0
            for token_id in lane.token_ids:
                _put_varint(output, _zigzag(token_id - previous_token))
                previous_token = token_id
        else:
            reference_index, reference_mode = token_reference
            _put_varint(output, (reference_index << 2) | reference_mode)

        _put_varint(output, len(lane.payload))
        output.extend(lane.payload)
    return bytes(output)


def structural_unpack(compact: bytes) -> bytes:
    if not compact.startswith(b"SV3") or len(compact) < 20:
        raise SieveError("invalid structural stream header")
    offset = 3
    packet_id = compact[offset : offset + 16]
    offset += 16
    flags = compact[offset]
    offset += 1
    generation, offset = _get_varint(compact, offset)
    sequence_cutoff, offset = _get_varint(compact, offset)
    token_budget, offset = _get_varint(compact, offset)
    breath_encoded, offset = _get_varint(compact, offset)
    breath_q1e6 = _unzigzag(breath_encoded)
    radius_q1e6, offset = _get_varint(compact, offset)
    lane_count, offset = _get_varint(compact, offset)
    hash_count, offset = _get_varint(compact, offset)
    if lane_count > 4096 or not 1 <= hash_count <= 8193:
        raise SieveError("structural count exceeds v1 limit")
    hash_bytes = hash_count * 32
    if offset + hash_bytes > len(compact):
        raise SieveError("truncated hash dictionary")
    hashes = [compact[index : index + 32] for index in range(offset, offset + hash_bytes, 32)]
    offset += hash_bytes
    if hashes[0] != ZERO_HASH or len(set(hashes)) != len(hashes):
        raise SieveError("invalid or duplicate hash dictionary")

    lanes: list[HeldContextLane] = []
    previous_lane_id = 0
    for _ in range(lane_count):
        lane_delta, offset = _get_varint(compact, offset)
        lane_id = previous_lane_id + lane_delta
        previous_lane_id = lane_id
        meta, offset = _get_varint(compact, offset)
        if meta >> 12:
            raise SieveError("unknown packed lane metadata bits")
        expiry_delta, offset = _get_varint(compact, offset)
        canonical_index, offset = _get_varint(compact, offset)
        source_index, offset = _get_varint(compact, offset)
        if canonical_index >= len(hashes) or source_index >= len(hashes):
            raise SieveError("hash dictionary index out of range")

        route_count, offset = _get_varint(compact, offset)
        if route_count > 256:
            raise SieveError("route dimension exceeds v1 limit")
        route: list[int] = []
        previous_coordinate = 0
        for _ in range(route_count):
            encoded, offset = _get_varint(compact, offset)
            coordinate = previous_coordinate + _unzigzag(encoded)
            if not -(1 << 31) <= coordinate < (1 << 31):
                raise SieveError("decoded route coordinate exceeds i32")
            route.append(coordinate)
            previous_coordinate = coordinate

        token_descriptor, offset = _get_varint(compact, offset)
        token_mode = token_descriptor & 0b11
        if token_mode:
            reference_index = token_descriptor >> 2
            try:
                decoded_role = LaneRole((meta >> 6) & 0b111)
            except ValueError as exc:
                raise SieveError("invalid packed lane role") from exc
            if reference_index >= len(lanes) or decoded_role != LaneRole.DERIVED:
                raise SieveError("invalid derived-token reference")
            prior = lanes[reference_index]
            if (
                not prior.flags & LaneFlags.EXACT_BYTES
                or prior.canonical_value_id != hashes[canonical_index]
                or prior.source_hash != hashes[source_index]
            ):
                raise SieveError("derived-token reference does not share exact provenance")
            width = {1: 1, 2: 2, 3: 4}[token_mode]
            if len(prior.payload) % width:
                raise SieveError("derived-token reference has incompatible payload width")
            tokens = [
                int.from_bytes(prior.payload[pos : pos + width], "little")
                for pos in range(0, len(prior.payload), width)
            ]
        else:
            token_count = token_descriptor >> 2
            if token_count > 1_048_576:
                raise SieveError("token count exceeds v1 limit")
            tokens = []
            previous_token = 0
            for _ in range(token_count):
                encoded, offset = _get_varint(compact, offset)
                token = previous_token + _unzigzag(encoded)
                if not 0 <= token <= 0xFFFFFFFF:
                    raise SieveError("decoded token ID exceeds u32")
                tokens.append(token)
                previous_token = token

        payload_len, offset = _get_varint(compact, offset)
        if payload_len > 8 * 1024 * 1024 or payload_len > len(compact) - offset:
            raise SieveError("truncated or oversized payload")
        payload = compact[offset : offset + payload_len]
        offset += payload_len
        try:
            expiry = 0xFFFFFFFFFFFFFFFF if expiry_delta == 0 else sequence_cutoff + expiry_delta - 1
            lane = HeldContextLane(
                lane_id=lane_id,
                kind=LaneKind(meta & 0b111),
                evidence=EvidenceState((meta >> 3) & 0b111),
                role=LaneRole((meta >> 6) & 0b111),
                flags=LaneFlags((meta >> 9) & 0b111),
                route_q1e6=tuple(route),
                token_ids=tuple(tokens),
                payload=payload,
                expiry_sequence=expiry,
                canonical_value_id=hashes[canonical_index],
                source_hash=hashes[source_index],
            )
        except (PacketError, ValueError) as exc:
            raise SieveError("invalid decoded lane") from exc
        lanes.append(lane)
    if offset != len(compact):
        raise SieveError("unclaimed bytes remain after structural stream")
    try:
        return HeldContextPacket(
            packet_id=packet_id,
            generation=generation,
            sequence_cutoff=sequence_cutoff,
            token_budget=token_budget,
            breath_q1e6=breath_q1e6,
            radius_q1e6=radius_q1e6,
            flags=flags,
            lanes=tuple(lanes),
        ).encode()
    except PacketError as exc:
        raise SieveError("decoded packet violates canonical contract") from exc


def compress_packet(raw_packet: bytes, *, deflate: bool = True) -> bytes:
    transformed = structural_pack(raw_packet)
    mode = MODE_DEFLATE if deflate else MODE_STRUCTURAL
    body = zlib.compress(transformed, level=9) if deflate else transformed
    header = WRAPPER.pack(
        SIEVE_MAGIC,
        SIEVE_VERSION,
        mode,
        0,
        len(raw_packet),
        len(transformed),
        zlib.crc32(raw_packet) & 0xFFFFFFFF,
        zlib.crc32(transformed) & 0xFFFFFFFF,
    )
    return header + body


def decompress_packet(encoded: bytes) -> bytes:
    if len(encoded) < WRAPPER.size:
        raise SieveError("truncated sieve wrapper")
    magic, version, mode, reserved, original_len, transformed_len, original_crc, transformed_crc = WRAPPER.unpack_from(
        encoded
    )
    if magic != SIEVE_MAGIC or version != SIEVE_VERSION or reserved != 0:
        raise SieveError("unsupported sieve wrapper")
    if original_len > 16 * 1024 * 1024 + 64 or transformed_len > MAX_TRANSFORMED_LEN:
        raise SieveError("declared sieve dimensions exceed v1 limits")
    body = encoded[WRAPPER.size :]
    if mode == MODE_STRUCTURAL:
        transformed = body
    elif mode == MODE_DEFLATE:
        decoder = zlib.decompressobj()
        try:
            transformed = decoder.decompress(body, transformed_len + 1)
        except zlib.error as exc:
            raise SieveError("invalid DEFLATE stream") from exc
        if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise SieveError("invalid or oversized DEFLATE stream")
    else:
        raise SieveError("unknown sieve compression mode")
    if len(transformed) != transformed_len or (zlib.crc32(transformed) & 0xFFFFFFFF) != transformed_crc:
        raise SieveError("transformed length or CRC mismatch")
    raw = structural_unpack(transformed)
    if len(raw) != original_len or (zlib.crc32(raw) & 0xFFFFFFFF) != original_crc:
        raise SieveError("original length or CRC mismatch")
    return raw


__all__ = [
    "SieveError",
    "compress_packet",
    "decompress_packet",
    "structural_pack",
    "structural_unpack",
]
