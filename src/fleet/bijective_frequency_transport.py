"""Bijective six-lane command transport with one-erasure recovery.

This module composes existing repository primitives without assigning them jobs
they do not perform:

* the semantic opcode VM supplies a compact, machine-checkable command tape;
* optional zlib compression removes repeated bytes;
* five data shards plus one XOR parity shard recover any single lost lane;
* six Sacred Tongues provide exact byte-token views and harmonic lane labels;
* per-lane and whole-payload SHA-256 values detect accidental corruption.

The orientation transforms and tongue views are bijections, not encryption.
SHA-256 values here are checksums, not authentication tags. An untrusted
transport still needs the repository's signed/AEAD or PQC envelope outside this
codec, and recovered commands still need governance before execution.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import zlib
from dataclasses import dataclass
from typing import Iterable, Literal

from python.scbe.semantic_opcode_vm import assemble, disassemble_text, parse_program
from src.crypto.sacred_tongues import TONGUES, SacredTongueTokenizer

SCHEMA_VERSION = "scbe_bijective_frequency_transport_v1"
TONGUE_ORDER = tuple(TONGUES)
DATA_LANE_COUNT = 5
PARITY_LANE_COUNT = 1

LaneRole = Literal["data", "parity"]
LaneTransform = Literal[
    "identity",
    "reverse",
    "invert",
    "reverse_invert",
    "rotate_left",
    "rotate_right",
]

LANE_TRANSFORMS: tuple[LaneTransform, ...] = (
    "identity",
    "reverse",
    "invert",
    "reverse_invert",
    "rotate_left",
    "rotate_right",
)


class BijectiveTransportError(ValueError):
    """Invalid, corrupted, or unrecoverable transport bundle."""


@dataclass(frozen=True, slots=True)
class FrequencyLane:
    """One transformed erasure-code shard assigned to a tongue/frequency lane."""

    index: int
    tongue: str
    harmonic_frequency_hz: float
    role: LaneRole
    transform: LaneTransform
    symbols: bytes
    symbol_sha256: str


@dataclass(frozen=True, slots=True)
class MultiplexedCommandBundle:
    """Immutable receipt for one encoded payload."""

    schema_version: str
    command_count: int
    source_utf8_bytes: int
    payload_bytes: int
    payload_sha256: str
    codec: str
    packed_bytes: int
    packed_sha256: str
    data_lane_count: int
    parity_lane_count: int
    shard_size: int
    lanes: tuple[FrequencyLane, ...]
    manifest_sha256: str

    @property
    def wire_symbol_bytes(self) -> int:
        """Payload symbols across every lane, excluding an outer envelope."""

        return sum(len(lane.symbols) for lane in self.lanes)

    @property
    def coding_overhead_ratio(self) -> float:
        """Erasure-coded symbols divided by packed payload bytes."""

        return self.wire_symbol_bytes / max(1, self.packed_bytes)


@dataclass(frozen=True, slots=True)
class PayloadRecovery:
    """Recovered bytes plus explicit erasure telemetry."""

    payload: bytes
    erased_lanes: tuple[str, ...]
    used_parity: bool


@dataclass(frozen=True, slots=True)
class ProgramRecovery:
    """Recovered semantic opcode tape and canonical command lines."""

    program: bytes
    commands: tuple[str, ...]
    erased_lanes: tuple[str, ...]
    used_parity: bool


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _transform(data: bytes, transform: LaneTransform) -> bytes:
    if transform == "identity":
        return data
    if transform == "reverse":
        return data[::-1]
    if transform == "invert":
        return bytes(value ^ 0xFF for value in data)
    if transform == "reverse_invert":
        return bytes(value ^ 0xFF for value in reversed(data))
    if transform == "rotate_left":
        return data[1:] + data[:1]
    if transform == "rotate_right":
        return data[-1:] + data[:-1]
    raise BijectiveTransportError(f"unknown lane transform: {transform}")


def _inverse_transform(data: bytes, transform: LaneTransform) -> bytes:
    if transform == "rotate_left":
        return _transform(data, "rotate_right")
    if transform == "rotate_right":
        return _transform(data, "rotate_left")
    return _transform(data, transform)


def _xor_shards(shards: Iterable[bytes]) -> bytes:
    material = tuple(shards)
    if not material:
        raise BijectiveTransportError("at least one shard is required")
    size = len(material[0])
    if any(len(shard) != size for shard in material):
        raise BijectiveTransportError("all shards must have equal length")
    parity = bytearray(size)
    for shard in material:
        for index, value in enumerate(shard):
            parity[index] ^= value
    return bytes(parity)


def _pack_payload(payload: bytes, *, allow_compression: bool) -> tuple[str, bytes]:
    if not allow_compression:
        return "identity", payload
    compressed = zlib.compress(payload, level=9)
    if len(compressed) < len(payload):
        return "zlib", compressed
    return "identity", payload


def _manifest_record(
    *,
    command_count: int,
    source_utf8_bytes: int,
    payload_bytes: int,
    payload_sha256: str,
    codec: str,
    packed_bytes: int,
    packed_sha256: str,
    shard_size: int,
    lanes: tuple[FrequencyLane, ...],
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "command_count": command_count,
        "source_utf8_bytes": source_utf8_bytes,
        "payload_bytes": payload_bytes,
        "payload_sha256": payload_sha256,
        "codec": codec,
        "packed_bytes": packed_bytes,
        "packed_sha256": packed_sha256,
        "data_lane_count": DATA_LANE_COUNT,
        "parity_lane_count": PARITY_LANE_COUNT,
        "shard_size": shard_size,
        "lanes": [
            {
                "index": lane.index,
                "tongue": lane.tongue,
                "harmonic_frequency_hz": lane.harmonic_frequency_hz,
                "role": lane.role,
                "transform": lane.transform,
                "symbol_bytes": len(lane.symbols),
                "symbol_sha256": lane.symbol_sha256,
            }
            for lane in lanes
        ],
    }


def _canonical_digest(record: dict[str, object]) -> str:
    encoded = json.dumps(
        record, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return _sha256(encoded)


def encode_payload(
    payload: bytes,
    *,
    command_count: int = 0,
    source_utf8_bytes: int = 0,
    allow_compression: bool = True,
) -> MultiplexedCommandBundle:
    """Encode bytes across five data lanes and one parity lane."""

    if command_count < 0 or source_utf8_bytes < 0:
        raise ValueError("command_count and source_utf8_bytes must be non-negative")
    payload = bytes(payload)
    codec, packed = _pack_payload(payload, allow_compression=allow_compression)
    shard_size = max(1, math.ceil(len(packed) / DATA_LANE_COUNT))
    padded = packed.ljust(shard_size * DATA_LANE_COUNT, b"\x00")
    data_shards = tuple(
        padded[index * shard_size : (index + 1) * shard_size]
        for index in range(DATA_LANE_COUNT)
    )
    parity = _xor_shards(data_shards)
    raw_shards = (*data_shards, parity)

    lanes = tuple(
        FrequencyLane(
            index=index,
            tongue=tongue,
            harmonic_frequency_hz=float(TONGUES[tongue].harmonic_frequency),
            role="data" if index < DATA_LANE_COUNT else "parity",
            transform=LANE_TRANSFORMS[index],
            symbols=(symbols := _transform(raw_shards[index], LANE_TRANSFORMS[index])),
            symbol_sha256=_sha256(symbols),
        )
        for index, tongue in enumerate(TONGUE_ORDER)
    )
    record = _manifest_record(
        command_count=command_count,
        source_utf8_bytes=source_utf8_bytes,
        payload_bytes=len(payload),
        payload_sha256=_sha256(payload),
        codec=codec,
        packed_bytes=len(packed),
        packed_sha256=_sha256(packed),
        shard_size=shard_size,
        lanes=lanes,
    )
    return MultiplexedCommandBundle(
        schema_version=SCHEMA_VERSION,
        command_count=command_count,
        source_utf8_bytes=source_utf8_bytes,
        payload_bytes=len(payload),
        payload_sha256=_sha256(payload),
        codec=codec,
        packed_bytes=len(packed),
        packed_sha256=_sha256(packed),
        data_lane_count=DATA_LANE_COUNT,
        parity_lane_count=PARITY_LANE_COUNT,
        shard_size=shard_size,
        lanes=lanes,
        manifest_sha256=_canonical_digest(record),
    )


def encode_program(
    source: str, *, allow_compression: bool = True
) -> MultiplexedCommandBundle:
    """Assemble a semicolon/newline command string, then encode its tape."""

    instructions = parse_program(source)
    program = assemble(source)
    return encode_payload(
        program,
        command_count=len(instructions),
        source_utf8_bytes=len(source.encode("utf-8")),
        allow_compression=allow_compression,
    )


def _validate_manifest(bundle: MultiplexedCommandBundle) -> None:
    if bundle.schema_version != SCHEMA_VERSION:
        raise BijectiveTransportError(f"unsupported schema: {bundle.schema_version}")
    if (
        bundle.data_lane_count != DATA_LANE_COUNT
        or bundle.parity_lane_count != PARITY_LANE_COUNT
    ):
        raise BijectiveTransportError("unsupported erasure-code geometry")
    if len(bundle.lanes) != len(TONGUE_ORDER):
        raise BijectiveTransportError("bundle must contain six lane records")
    for index, (lane, tongue, transform) in enumerate(
        zip(bundle.lanes, TONGUE_ORDER, LANE_TRANSFORMS)
    ):
        if (
            lane.index != index
            or lane.tongue != tongue
            or lane.transform != transform
            or lane.role != ("data" if index < DATA_LANE_COUNT else "parity")
            or len(lane.symbols) != bundle.shard_size
        ):
            raise BijectiveTransportError(f"invalid lane metadata at index {index}")
    record = _manifest_record(
        command_count=bundle.command_count,
        source_utf8_bytes=bundle.source_utf8_bytes,
        payload_bytes=bundle.payload_bytes,
        payload_sha256=bundle.payload_sha256,
        codec=bundle.codec,
        packed_bytes=bundle.packed_bytes,
        packed_sha256=bundle.packed_sha256,
        shard_size=bundle.shard_size,
        lanes=bundle.lanes,
    )
    expected = _canonical_digest(record)
    if not hmac.compare_digest(expected, bundle.manifest_sha256):
        raise BijectiveTransportError("manifest checksum mismatch")


def recover_payload(
    bundle: MultiplexedCommandBundle,
    *,
    unavailable_lanes: Iterable[str] = (),
) -> PayloadRecovery:
    """Recover a payload after zero or one lane erasure/corruption."""

    _validate_manifest(bundle)
    unavailable = set(unavailable_lanes)
    unknown = unavailable.difference(TONGUE_ORDER)
    if unknown:
        raise BijectiveTransportError(f"unknown unavailable lanes: {sorted(unknown)}")

    shards: list[bytes | None] = [None] * len(TONGUE_ORDER)
    erased = set(unavailable)
    for lane in bundle.lanes:
        if lane.tongue in unavailable:
            continue
        if not hmac.compare_digest(_sha256(lane.symbols), lane.symbol_sha256):
            erased.add(lane.tongue)
            continue
        shards[lane.index] = _inverse_transform(lane.symbols, lane.transform)

    missing_data = [index for index in range(DATA_LANE_COUNT) if shards[index] is None]
    parity = shards[DATA_LANE_COUNT]
    used_parity = False
    if len(missing_data) > 1:
        raise BijectiveTransportError("more than one data lane is unavailable")
    if missing_data:
        if parity is None:
            raise BijectiveTransportError(
                "data lane and parity lane are both unavailable"
            )
        missing_index = missing_data[0]
        known = [
            shard
            for index, shard in enumerate(shards[:DATA_LANE_COUNT])
            if index != missing_index
        ]
        if any(shard is None for shard in known):
            raise BijectiveTransportError("insufficient data shards")
        shards[missing_index] = _xor_shards(
            (parity, *(shard for shard in known if shard is not None))
        )
        used_parity = True
    elif parity is not None:
        expected_parity = _xor_shards(
            shard for shard in shards[:DATA_LANE_COUNT] if shard is not None
        )
        if not hmac.compare_digest(expected_parity, parity):
            raise BijectiveTransportError("parity mismatch")

    data_shards = shards[:DATA_LANE_COUNT]
    if any(shard is None for shard in data_shards):
        raise BijectiveTransportError("payload reconstruction incomplete")
    packed = b"".join(shard for shard in data_shards if shard is not None)[
        : bundle.packed_bytes
    ]
    if not hmac.compare_digest(_sha256(packed), bundle.packed_sha256):
        raise BijectiveTransportError("packed payload checksum mismatch")

    if bundle.codec == "identity":
        payload = packed
    elif bundle.codec == "zlib":
        try:
            payload = zlib.decompress(packed)
        except zlib.error as exc:
            raise BijectiveTransportError("compressed payload is invalid") from exc
    else:
        raise BijectiveTransportError(f"unsupported codec: {bundle.codec}")
    if len(payload) != bundle.payload_bytes or not hmac.compare_digest(
        _sha256(payload), bundle.payload_sha256
    ):
        raise BijectiveTransportError("recovered payload checksum mismatch")
    return PayloadRecovery(
        payload=payload, erased_lanes=tuple(sorted(erased)), used_parity=used_parity
    )


def recover_program(
    bundle: MultiplexedCommandBundle,
    *,
    unavailable_lanes: Iterable[str] = (),
) -> ProgramRecovery:
    """Recover and disassemble the tape without executing it."""

    recovery = recover_payload(bundle, unavailable_lanes=unavailable_lanes)
    commands = tuple(disassemble_text(recovery.payload))
    if len(commands) != bundle.command_count:
        raise BijectiveTransportError("command count does not match manifest")
    return ProgramRecovery(
        program=recovery.payload,
        commands=commands,
        erased_lanes=recovery.erased_lanes,
        used_parity=recovery.used_parity,
    )


def prove_lane_token_bijections(
    bundle: MultiplexedCommandBundle,
    tokenizer: SacredTongueTokenizer | None = None,
) -> dict[str, bool]:
    """Prove each lane survives its assigned Sacred Tongue byte-token view."""

    tok = tokenizer or SacredTongueTokenizer()
    return {
        lane.tongue: tok.decode_tokens(
            lane.tongue, tok.encode_bytes(lane.tongue, lane.symbols)
        )
        == lane.symbols
        for lane in bundle.lanes
    }


def bundle_metrics(bundle: MultiplexedCommandBundle) -> dict[str, int | float | str]:
    """Return explicit density and redundancy accounting."""

    return {
        "commands": bundle.command_count,
        "source_utf8_bytes": bundle.source_utf8_bytes,
        "opcode_bytes": bundle.payload_bytes,
        "codec": bundle.codec,
        "packed_bytes": bundle.packed_bytes,
        "wire_symbol_bytes": bundle.wire_symbol_bytes,
        "source_to_opcode_ratio": bundle.source_utf8_bytes
        / max(1, bundle.payload_bytes),
        "opcode_to_packed_ratio": bundle.payload_bytes / max(1, bundle.packed_bytes),
        "coding_overhead_ratio": bundle.coding_overhead_ratio,
    }


__all__ = [
    "BijectiveTransportError",
    "DATA_LANE_COUNT",
    "FrequencyLane",
    "LANE_TRANSFORMS",
    "MultiplexedCommandBundle",
    "PARITY_LANE_COUNT",
    "PayloadRecovery",
    "ProgramRecovery",
    "SCHEMA_VERSION",
    "TONGUE_ORDER",
    "bundle_metrics",
    "encode_payload",
    "encode_program",
    "prove_lane_token_bijections",
    "recover_payload",
    "recover_program",
]
