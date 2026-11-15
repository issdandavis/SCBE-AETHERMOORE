"""Canonical held-context packet v1.

The packet is a language-neutral storage and transport contract.  It preserves
exact bytes, typed evidence state, provenance hashes, token IDs, and optional
fixed-point route coordinates.  Geometry is metadata for routing; it is not an
authorization decision and it does not create information absent from the
payload.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, IntFlag
import struct
from typing import Callable, Iterable
import zlib

MAGIC = b"HCTX"
VERSION = 1
HEADER_LEN = 64
LANE_HEADER_LEN = 96
Q_SCALE = 1_000_000
MAX_BODY_LEN = 16 * 1024 * 1024
MAX_LANES = 4096
MAX_ROUTE_DIM = 256
MAX_TOKEN_COUNT = 1_048_576
MAX_PAYLOAD_LEN = 8 * 1024 * 1024
NO_EXPIRY = (1 << 64) - 1
ZERO_HASH = bytes(32)

HEADER_STRUCT = struct.Struct("<4sBBHIHHQIii16sIII")
LANE_STRUCT = struct.Struct("<HBBBBHIIQ32s32sII")


class PacketError(ValueError):
    """Raised when bytes do not satisfy the v1 packet contract."""


class LaneKind(IntEnum):
    ROOT = 0
    LINGUISTIC = 1
    ROUTE = 2
    TOOL = 3
    SPEECH = 4
    GEOMETRY = 5
    RECEIPT = 6
    CUSTOM = 7


class EvidenceState(IntEnum):
    PRESENT = 0
    MISSING = 1
    NEUTRAL = 2
    SILENCE = 3
    ABSTAIN = 4


class LaneRole(IntEnum):
    INDEPENDENT = 0
    DERIVED = 1
    CONTROL = 2
    OBSERVED = 3
    COMPUTED = 4
    PROVENANCE = 5


class LaneFlags(IntFlag):
    NONE = 0
    PINNED = 1 << 0
    COMPRESSIBLE = 1 << 1
    EXACT_BYTES = 1 << 2


KNOWN_LANE_FLAGS = int(LaneFlags.PINNED | LaneFlags.COMPRESSIBLE | LaneFlags.EXACT_BYTES)


def _crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def _require_hash(name: str, value: bytes) -> None:
    if not isinstance(value, bytes) or len(value) != 32:
        raise PacketError(f"{name} must be exactly 32 bytes")


def _require_enum(enum_type: type[IntEnum], value: IntEnum, name: str) -> None:
    try:
        enum_type(int(value))
    except (TypeError, ValueError) as exc:
        raise PacketError(f"invalid {name}: {value!r}") from exc


@dataclass(frozen=True, slots=True)
class HeldContextLane:
    lane_id: int
    kind: LaneKind
    evidence: EvidenceState
    role: LaneRole
    flags: LaneFlags = LaneFlags.NONE
    route_q1e6: tuple[int, ...] = ()
    token_ids: tuple[int, ...] = ()
    payload: bytes = b""
    expiry_sequence: int = NO_EXPIRY
    canonical_value_id: bytes = ZERO_HASH
    source_hash: bytes = ZERO_HASH

    def validate(self) -> None:
        if isinstance(self.lane_id, bool) or not 0 <= self.lane_id <= 0xFFFF:
            raise PacketError("lane_id must fit u16")
        _require_enum(LaneKind, self.kind, "lane kind")
        _require_enum(EvidenceState, self.evidence, "evidence state")
        _require_enum(LaneRole, self.role, "lane role")
        if int(self.flags) & ~KNOWN_LANE_FLAGS:
            raise PacketError("unknown lane flag bit")
        if len(self.route_q1e6) > MAX_ROUTE_DIM:
            raise PacketError("route dimension exceeds v1 limit")
        if len(self.token_ids) > MAX_TOKEN_COUNT:
            raise PacketError("token count exceeds v1 limit")
        if len(self.payload) > MAX_PAYLOAD_LEN:
            raise PacketError("payload exceeds v1 limit")
        if not 0 <= self.expiry_sequence <= NO_EXPIRY:
            raise PacketError("expiry_sequence must fit u64")
        if any(isinstance(value, bool) or not -(1 << 31) <= value < (1 << 31) for value in self.route_q1e6):
            raise PacketError("route coordinate must fit signed i32")
        if any(isinstance(value, bool) or not 0 <= value <= 0xFFFFFFFF for value in self.token_ids):
            raise PacketError("token ID must fit u32")
        if not isinstance(self.payload, bytes):
            raise PacketError("payload must be bytes")
        _require_hash("canonical_value_id", self.canonical_value_id)
        _require_hash("source_hash", self.source_hash)

    def encode(self) -> bytes:
        self.validate()
        variable = b"".join(
            (
                struct.pack(f"<{len(self.route_q1e6)}i", *self.route_q1e6),
                struct.pack(f"<{len(self.token_ids)}I", *self.token_ids),
                self.payload,
            )
        )
        prefix = LANE_STRUCT.pack(
            self.lane_id,
            int(self.kind),
            int(self.evidence),
            int(self.role),
            int(self.flags),
            len(self.route_q1e6),
            len(self.token_ids),
            len(self.payload),
            self.expiry_sequence,
            self.canonical_value_id,
            self.source_hash,
            0,
            0,
        )
        lane_crc = _crc32(prefix[:88] + variable)
        return prefix[:88] + struct.pack("<II", lane_crc, 0) + variable


@dataclass(frozen=True, slots=True)
class HeldContextPacket:
    packet_id: bytes
    generation: int
    sequence_cutoff: int
    token_budget: int
    breath_q1e6: int = Q_SCALE
    radius_q1e6: int = 0
    flags: int = 0
    lanes: tuple[HeldContextLane, ...] = ()

    def validate(self) -> None:
        if not isinstance(self.packet_id, bytes) or len(self.packet_id) != 16:
            raise PacketError("packet_id must be exactly 16 bytes")
        if not 0 <= self.flags <= 0xFF:
            raise PacketError("packet flags must fit u8")
        if not 0 <= self.generation <= 0xFFFFFFFF:
            raise PacketError("generation must fit u32")
        if not 0 <= self.sequence_cutoff <= NO_EXPIRY:
            raise PacketError("sequence_cutoff must fit u64")
        if not 0 <= self.token_budget <= 0xFFFFFFFF:
            raise PacketError("token_budget must fit u32")
        for name, value in (("breath_q1e6", self.breath_q1e6), ("radius_q1e6", self.radius_q1e6)):
            if isinstance(value, bool) or not -(1 << 31) <= value < (1 << 31):
                raise PacketError(f"{name} must fit signed i32")
        if not 0 <= self.radius_q1e6 < Q_SCALE:
            raise PacketError("radius_q1e6 must represent a point inside the unit ball")
        if len(self.lanes) > MAX_LANES:
            raise PacketError("lane count exceeds v1 limit")
        ids = [lane.lane_id for lane in self.lanes]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise PacketError("lanes must have unique ascending lane_id values")
        for lane in self.lanes:
            lane.validate()
            if lane.expiry_sequence != NO_EXPIRY and lane.expiry_sequence < self.sequence_cutoff:
                raise PacketError("packet contains a lane expired before sequence_cutoff")

    def encode(self) -> bytes:
        self.validate()
        body = b"".join(lane.encode() for lane in self.lanes)
        if len(body) > MAX_BODY_LEN:
            raise PacketError("packet body exceeds v1 limit")
        body_crc = _crc32(body)
        header = HEADER_STRUCT.pack(
            MAGIC,
            VERSION,
            self.flags,
            HEADER_LEN,
            len(body),
            len(self.lanes),
            0,
            self.sequence_cutoff,
            self.token_budget,
            self.breath_q1e6,
            self.radius_q1e6,
            self.packet_id,
            self.generation,
            body_crc,
            0,
        )
        header_crc = _crc32(header[:60])
        return header[:60] + struct.pack("<I", header_crc) + body


def decode_packet(raw: bytes) -> HeldContextPacket:
    """Decode and validate one packet, rejecting trailing or malformed bytes."""

    if not isinstance(raw, bytes):
        raise PacketError("packet input must be bytes")
    if len(raw) < HEADER_LEN:
        raise PacketError("truncated packet header")
    (
        magic,
        version,
        flags,
        header_len,
        body_len,
        lane_count,
        reserved,
        sequence_cutoff,
        token_budget,
        breath_q1e6,
        radius_q1e6,
        packet_id,
        generation,
        body_crc,
        header_crc,
    ) = HEADER_STRUCT.unpack_from(raw)
    if magic != MAGIC or version != VERSION or header_len != HEADER_LEN:
        raise PacketError("unsupported packet magic, version, or header length")
    if reserved != 0:
        raise PacketError("packet reserved field must be zero")
    if body_len > MAX_BODY_LEN or lane_count > MAX_LANES:
        raise PacketError("declared packet dimensions exceed v1 limits")
    if len(raw) != HEADER_LEN + body_len:
        raise PacketError("packet length does not match body_len")
    if _crc32(raw[:60]) != header_crc:
        raise PacketError("header CRC mismatch")
    body = raw[HEADER_LEN:]
    if _crc32(body) != body_crc:
        raise PacketError("body CRC mismatch")

    lanes: list[HeldContextLane] = []
    offset = 0
    for _ in range(lane_count):
        if body_len - offset < LANE_HEADER_LEN:
            raise PacketError("truncated lane header")
        lane_header = body[offset : offset + LANE_HEADER_LEN]
        (
            lane_id,
            kind_raw,
            evidence_raw,
            role_raw,
            lane_flags,
            route_dim,
            token_count,
            payload_len,
            expiry_sequence,
            canonical_value_id,
            source_hash,
            lane_crc,
            lane_reserved,
        ) = LANE_STRUCT.unpack(lane_header)
        if lane_reserved != 0:
            raise PacketError("lane reserved field must be zero")
        if route_dim > MAX_ROUTE_DIM or token_count > MAX_TOKEN_COUNT or payload_len > MAX_PAYLOAD_LEN:
            raise PacketError("declared lane dimensions exceed v1 limits")
        variable_len = route_dim * 4 + token_count * 4 + payload_len
        lane_end = offset + LANE_HEADER_LEN + variable_len
        if lane_end > body_len:
            raise PacketError("truncated lane variable data")
        variable = body[offset + LANE_HEADER_LEN : lane_end]
        if _crc32(lane_header[:88] + variable) != lane_crc:
            raise PacketError(f"lane {lane_id} CRC mismatch")
        route_end = route_dim * 4
        token_end = route_end + token_count * 4
        route = struct.unpack(f"<{route_dim}i", variable[:route_end]) if route_dim else ()
        tokens = struct.unpack(f"<{token_count}I", variable[route_end:token_end]) if token_count else ()
        try:
            lane = HeldContextLane(
                lane_id=lane_id,
                kind=LaneKind(kind_raw),
                evidence=EvidenceState(evidence_raw),
                role=LaneRole(role_raw),
                flags=LaneFlags(lane_flags),
                route_q1e6=tuple(route),
                token_ids=tuple(tokens),
                payload=variable[token_end:],
                expiry_sequence=expiry_sequence,
                canonical_value_id=canonical_value_id,
                source_hash=source_hash,
            )
        except ValueError as exc:
            raise PacketError(f"lane {lane_id} contains an unknown enum value") from exc
        lane.validate()
        lanes.append(lane)
        offset = lane_end
    if offset != body_len:
        raise PacketError("unclaimed bytes remain after final lane")

    packet = HeldContextPacket(
        packet_id=packet_id,
        generation=generation,
        sequence_cutoff=sequence_cutoff,
        token_budget=token_budget,
        breath_q1e6=breath_q1e6,
        radius_q1e6=radius_q1e6,
        flags=flags,
        lanes=tuple(lanes),
    )
    packet.validate()
    return packet


def build_linguistic_lanes(
    *,
    first_lane_id: int,
    text: str,
    tokenizer: Callable[[str], Iterable[int]],
    canonical_value_id: bytes,
    source_hash: bytes,
) -> tuple[HeldContextLane, HeldContextLane]:
    """Preserve source UTF-8 and attach a deterministic derived token view."""

    exact = HeldContextLane(
        lane_id=first_lane_id,
        kind=LaneKind.LINGUISTIC,
        evidence=EvidenceState.PRESENT,
        role=LaneRole.OBSERVED,
        flags=LaneFlags.PINNED | LaneFlags.EXACT_BYTES,
        payload=text.encode("utf-8"),
        canonical_value_id=canonical_value_id,
        source_hash=source_hash,
    )
    token_view = HeldContextLane(
        lane_id=first_lane_id + 1,
        kind=LaneKind.LINGUISTIC,
        evidence=EvidenceState.PRESENT,
        role=LaneRole.DERIVED,
        flags=LaneFlags.COMPRESSIBLE,
        token_ids=tuple(tokenizer(text)),
        canonical_value_id=canonical_value_id,
        source_hash=source_hash,
    )
    return exact, token_view


def select_visible_lanes(packet: HeldContextPacket, *, current_sequence: int) -> tuple[HeldContextLane, ...]:
    """Return lanes visible at a monotonic sequence without future leakage."""

    if current_sequence < packet.sequence_cutoff:
        raise PacketError("current_sequence precedes packet sequence_cutoff")
    return tuple(
        lane for lane in packet.lanes if lane.expiry_sequence == NO_EXPIRY or current_sequence <= lane.expiry_sequence
    )


__all__ = [
    "EvidenceState",
    "HeldContextLane",
    "HeldContextPacket",
    "LaneFlags",
    "LaneKind",
    "LaneRole",
    "NO_EXPIRY",
    "PacketError",
    "Q_SCALE",
    "build_linguistic_lanes",
    "decode_packet",
    "select_visible_lanes",
]
