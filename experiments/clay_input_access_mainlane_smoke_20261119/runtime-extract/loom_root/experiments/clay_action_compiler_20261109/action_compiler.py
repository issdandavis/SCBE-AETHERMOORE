#!/usr/bin/env python3
"""Deterministic input -> token -> geometry -> compiled action -> speech.

This is Clay's action-oriented first-layer prototype.  Immutable integer
weight rows perform dispatch, but an independent registry, finite Klein gate,
and each executor's own parser must all agree before anything runs.  Tool calls
stop at the existing static sandbox seal; this module has no side-effecting tool
dispatcher.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import zlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
LOOM_ROOT = HERE.parents[1]
SCBE_ROOT_CANDIDATES = (
    Path(os.environ.get("SCBE_ROOT", "")),
    Path(r"C:\Users\issda\SCBE-AETHERMOORE"),
    Path(r"C:\dev\SCBE-AETHERMOORE"),
    Path(r"C:\dev\.repos_clone\SCBE-AETHERMOORE"),
)


def _prepare_import_paths() -> tuple[Path, Path]:
    """Install the measured SCBE path order: python package before repo root."""

    scbe_root = next(
        (
            candidate
            for candidate in SCBE_ROOT_CANDIDATES
            if candidate and (candidate / "python" / "scbe" / "instrument.py").is_file()
        ),
        None,
    )
    if scbe_root is None:
        searched = ", ".join(str(path) for path in SCBE_ROOT_CANDIDATES if path)
        raise ImportError(f"SCBE checkout not found; searched: {searched}")
    scbe_python = scbe_root / "python"
    for path in (str(LOOM_ROOT), str(scbe_root)):
        if path not in sys.path:
            sys.path.append(path)
    if str(scbe_python) in sys.path:
        sys.path.remove(str(scbe_python))
    sys.path.insert(0, str(scbe_python))
    os.environ.setdefault("SCBE_PYTHON", str(scbe_python))
    return scbe_root, scbe_python


SCBE_ROOT, SCBE_PYTHON = _prepare_import_paths()

from clay_rubix_surface import (  # noqa: E402
    Slot,
    addr_to_byte,
    all_slots,
    byte_to_addr,
    cell,
    dual,
    stochastic_views,
    to_base,
    to_depth,
)
from clay_tool_sandbox import static_seal  # noqa: E402
from loom_multiplex import (  # noqa: E402
    Address,
    address_domain,
    bind_renewal,
    cell_record,
    children,
    cross_day,
    cube_walls,
    opcode_xyz,
    radial_phone_coordinate,
    renewal_successors,
    reverse_route,
    round_trip_movement,
    route,
    run_entity_core,
    shortest_cell_route,
    tongue_forms,
)
from quine_state_playground import quine_seeded_region  # noqa: E402
from tongues.opcode_compose import compute  # noqa: E402
from tongues.tongue_opcodes import ORDER as TONGUE_ORDER  # noqa: E402
from tongues.tongue_opcodes import render as render_tongue  # noqa: E402
from scbe.atomic_tokenization import map_token_to_atomic_state  # noqa: E402
from scbe.instrument import _NAME_TO_BYTE, ca_word_for_opcode  # noqa: E402
from python.scbe.bit_spine import BitSpineError  # noqa: E402
from python.scbe.turing_rubix import run_moves  # noqa: E402


def _load_local_speech_module():
    """Bind speech blocks to this worktree, not a previously imported lane."""

    path = LOOM_ROOT / "block_speech.py"
    spec = importlib.util.spec_from_file_location("_clay_action_block_speech", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load local speech blocks from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SPEECH = _load_local_speech_module()
compile_observation = _SPEECH.compile_observation
speech_block_table = _SPEECH.speech_block_table
speak = _SPEECH.speak


SCHEMA = "clay.action-compiler.v2"
TAPE_SCHEMA = "clay.action-tape.v2"
TAPE_SEAL_SCHEMA = "clay.action-tape-chain-seal.v1"
ACTION_PACKET_SCHEMA = "clay.action-token-packet.v1"
ACTION_PACKET_MAGIC = b"\xCA\x1A"
ACTION_PACKET_VERSION = 1
ACTION_PACKET_HEADER_BYTES = 8
ACTION_PACKET_CRC_BYTES = 4
MAX_INPUT_BYTES = 4096
MAX_TAPE_FRAMES = 256
FAMILY_ORDER = ("math", "rubix", "tool", "loom")

# Columns:
# executor, tongue-index, Rubix-face, sandbox, speech, trit-x, trit-y, trit-z.
# Selecting a token constructs a one-hot vector and multiplies it by this table.
# The selected integer row is the executable dispatch state: changing it changes
# the executor or fails one of the independent seals below.
COMPILER_WEIGHT_MATRIX: tuple[tuple[int, ...], ...] = (
    (1, 3, 4, 0, 1, -1, 0, 1),   # math  -> CA, face 4, pure execution
    (2, 2, 3, 0, 1, 0, 1, -1),   # rubix -> RU, face 3, pure execution
    (3, 1, 2, 1, 1, 1, -1, 0),   # tool  -> AV, face 2, static seal only
    (4, 0, 1, 0, 1, 1, 0, -1),   # loom  -> KO, face 1, pure execution
)
TRANSPORT_BYTES = {"math": 0xC0, "rubix": 0xC1, "tool": 0xC2, "loom": 0xC3}
GEOMETRY_SEEDS = {
    "math": (-0.25, 0.0),
    "rubix": (0.0, 0.25),
    "tool": (0.25, -0.25),
    "loom": (0.25, 0.0),
}
GEOMETRY_REGION_RADIUS = 0.20
ACTION_CARRIER_LEXEMES = {
    "math": "think",
    "rubix": "run",
    "tool": "build",
    "loom": "run",
}

# The second compiler level is a typed method table.  Its values are not
# handwritten labels: each row is derived from its canonical method index by
# ``radial_power_weight`` below.  Bytes remain disjoint by family so the same
# surface spelling can never silently select a method in another executor.
METHOD_TRANSPORT_BYTES: dict[str, dict[str, int]] = {
    "rubix": {
        "moves": 0xD0,
        "dual": 0xD1,
        "slot": 0xD2,
        "encode": 0xD3,
        "decode": 0xD4,
        "address": 0xD5,
        "byte": 0xD6,
        "slots": 0xD7,
        "views": 0xD8,
    },
    "loom": {
        "route": 0xE0,
        "cell": 0xE1,
        "tongues": 0xE2,
        "radial": 0xE3,
        "entity": 0xE4,
        "xyz": 0xE5,
        "shortest": 0xE6,
        "renewal": 0xE7,
        "bind": 0xE8,
        "cross_day": 0xE9,
        "domain": 0xEA,
        "walls": 0xEB,
        "children": 0xEC,
    },
}

# V2 receipts used five rows per typed family. New rows are appended and use a
# wider radial ring, but these prefix counts keep every existing row exactly
# stable. Token IDs and transport bytes are therefore backward compatible.
LEGACY_METHOD_COUNTS = {"rubix": 5, "loom": 5}


class ActionCompileError(ValueError):
    """The input could not pass an exact compiler boundary."""


@dataclass(frozen=True, slots=True)
class ActionToken:
    family: str
    token_id: int
    source_token: str
    source_tongue: str
    payload: str
    transport_byte: int


@dataclass(frozen=True, slots=True)
class CompilerWeightRow:
    executor_code: int
    tongue_index: int
    face: int
    sandbox_code: int
    speech_code: int
    trits: tuple[int, int, int]

    @classmethod
    def decode(cls, values: tuple[int, ...]) -> "CompilerWeightRow":
        if len(values) != 8:
            raise ActionCompileError("compiler weight row must have eight values")
        row = cls(
            executor_code=values[0],
            tongue_index=values[1],
            face=values[2],
            sandbox_code=values[3],
            speech_code=values[4],
            trits=(values[5], values[6], values[7]),
        )
        if any(value not in {-1, 0, 1} for value in row.trits):
            raise ActionCompileError("compiler trits must be balanced {-1,0,+1}")
        if not 0 <= row.tongue_index < len(TONGUE_ORDER):
            raise ActionCompileError("compiler tongue index is out of range")
        if row.face not in range(1, 7):
            raise ActionCompileError("compiler Rubix face is out of range")
        if row.sandbox_code not in {0, 1} or row.speech_code != 1:
            raise ActionCompileError("compiler sandbox/speech mode is not authorized")
        return row

    def as_dict(self) -> dict[str, Any]:
        return {
            "executor_code": self.executor_code,
            "tongue_index": self.tongue_index,
            "tongue": TONGUE_ORDER[self.tongue_index],
            "face": self.face,
            "sandbox_code": self.sandbox_code,
            "speech_code": self.speech_code,
            "trits": list(self.trits),
        }


@dataclass(frozen=True, slots=True)
class MethodToken:
    family: str
    method: str
    method_id: int
    source_token: str
    source_tongue: str
    payload: str
    transport_byte: int


@dataclass(frozen=True, slots=True)
class MethodWeightRow:
    method_code: int
    tongue_index: int
    face: int
    trits: tuple[int, int, int]
    phase_numerator: int
    phase_denominator: int
    power_residue: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "method_code": self.method_code,
            "tongue_index": self.tongue_index,
            "tongue": TONGUE_ORDER[self.tongue_index],
            "face": self.face,
            "trits": list(self.trits),
            "radial_phase": {
                "numerator": self.phase_numerator,
                "denominator": self.phase_denominator,
            },
            "power_residue": self.power_residue,
        }


def _balanced_trits(value: int, width: int = 3) -> tuple[int, ...]:
    """Return a fixed-width, least-significant-first balanced-ternary address."""

    if value < 0 or width < 1:
        raise ValueError("balanced-trit source must be non-negative and width positive")
    out: list[int] = []
    carry = value
    for _ in range(width):
        digit = carry % 3
        carry //= 3
        if digit == 2:
            digit = -1
            carry += 1
        out.append(digit)
    return tuple(out)


def radial_power_weight(method_id: int, method_count: int) -> MethodWeightRow:
    """Algebraically derive one exact method row from a bounded radial ring.

    The phase denominator is the next power-of-two ring that can hold every
    method.  A modular power supplies a stable integer residue, which is then
    projected into face, tongue, and balanced-trit coordinates.  No text label
    participates in the arithmetic dispatch row.
    """

    if not 0 <= method_id < method_count:
        raise ValueError("method id lies outside its bounded method table")
    ring = 1 << max(1, (method_count - 1).bit_length())
    residue = pow(3, method_id + 1, 257)
    trits = _balanced_trits(residue, width=3)
    return MethodWeightRow(
        method_code=method_id + 1,
        tongue_index=residue % len(TONGUE_ORDER),
        face=(residue % 6) + 1,
        trits=(int(trits[0]), int(trits[1]), int(trits[2])),
        phase_numerator=method_id,
        phase_denominator=ring,
        power_residue=residue,
    )


@dataclass(frozen=True, slots=True)
class ExecutionPacket:
    value: Any
    speech_value: Any
    lowered_tokens: tuple[dict[str, Any], ...]
    details: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ActionFrame:
    """Tokenizer-native action input; no family or method text is required."""

    family_token_id: int
    payload: str
    method_token_id: int | None = None
    source_tongue: str = "EN"


@dataclass(frozen=True, slots=True)
class ActionPacket:
    """Byte-native action transport decoded through exact token registries.

    The packet carries transport bytes, not family or method names. Payload
    bytes remain bounded UTF-8 because the current pure executors expose exact
    textual argument grammars. The CRC detects transport damage; the compiled
    action receipt still supplies the cryptographic execution seal.
    """

    family_transport_byte: int
    method_transport_byte: int
    source_tongue_id: int
    payload: bytes


@dataclass(frozen=True, slots=True)
class ActionTape:
    """A bounded ordered program of tokenizer-native action frames."""

    frames: tuple[ActionFrame, ...]


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def encode_action_packet(frame: ActionFrame) -> bytes:
    """Encode a tokenizer-native frame as a bounded deterministic byte packet."""

    if not isinstance(frame, ActionFrame):
        raise TypeError("encode_action_packet expects an ActionFrame")
    if not 0 <= frame.family_token_id < len(FAMILY_ORDER):
        raise ActionCompileError("family token id is outside the compiler table")
    tongue_order = ("EN", *TONGUE_ORDER)
    if frame.source_tongue not in tongue_order:
        raise ActionCompileError("source tongue is outside the six-tongue table")
    if not isinstance(frame.payload, str) or not frame.payload.strip():
        raise ActionCompileError("action frame payload must be non-empty text")
    payload = frame.payload.strip().encode("utf-8")
    if len(payload) > MAX_INPUT_BYTES:
        raise ActionCompileError("action frame payload exceeds the byte limit")

    family = FAMILY_ORDER[frame.family_token_id]
    method_byte = 0
    if family in METHOD_TRANSPORT_BYTES:
        methods = tuple(METHOD_TRANSPORT_BYTES[family])
        method_id = 0 if frame.method_token_id is None else frame.method_token_id
        if not 0 <= method_id < len(methods):
            raise ActionCompileError("method token id is outside the family table")
        method_byte = METHOD_TRANSPORT_BYTES[family][methods[method_id]]
    elif frame.method_token_id is not None:
        raise ActionCompileError("this family does not accept a method token")

    header = bytes((
        *ACTION_PACKET_MAGIC,
        ACTION_PACKET_VERSION,
        TRANSPORT_BYTES[family],
        method_byte,
        tongue_order.index(frame.source_tongue),
        (len(payload) >> 8) & 0xFF,
        len(payload) & 0xFF,
    ))
    body = header + payload
    return body + zlib.crc32(body).to_bytes(ACTION_PACKET_CRC_BYTES, "big")


def decode_action_packet(encoded: bytes) -> tuple[ActionPacket, ActionFrame]:
    """Decode and registry-check one byte-native action packet."""

    if not isinstance(encoded, bytes):
        raise TypeError("decode_action_packet expects bytes")
    minimum = ACTION_PACKET_HEADER_BYTES + ACTION_PACKET_CRC_BYTES + 1
    if len(encoded) < minimum:
        raise ActionCompileError("action packet is truncated")
    body = encoded[:-ACTION_PACKET_CRC_BYTES]
    observed_crc = int.from_bytes(encoded[-ACTION_PACKET_CRC_BYTES:], "big")
    if zlib.crc32(body) != observed_crc:
        raise ActionCompileError("action packet CRC does not match")
    if body[:2] != ACTION_PACKET_MAGIC:
        raise ActionCompileError("action packet magic does not match")
    if body[2] != ACTION_PACKET_VERSION:
        raise ActionCompileError("action packet version is unsupported")

    family_byte, method_byte, tongue_id = body[3], body[4], body[5]
    payload_size = int.from_bytes(body[6:8], "big")
    payload = body[ACTION_PACKET_HEADER_BYTES:]
    if payload_size != len(payload) or not 0 < payload_size <= MAX_INPUT_BYTES:
        raise ActionCompileError("action packet payload length does not match")

    family_by_byte = {byte: family for family, byte in TRANSPORT_BYTES.items()}
    family = family_by_byte.get(family_byte)
    if family is None:
        raise ActionCompileError("action packet family byte is unknown")
    family_token_id = FAMILY_ORDER.index(family)

    method_token_id: int | None = None
    if family in METHOD_TRANSPORT_BYTES:
        method_by_byte = {
            byte: index
            for index, byte in enumerate(METHOD_TRANSPORT_BYTES[family].values())
        }
        method_token_id = method_by_byte.get(method_byte)
        if method_token_id is None:
            raise ActionCompileError("action packet method byte is unknown for its family")
    elif method_byte != 0:
        raise ActionCompileError("action packet method byte is invalid for its family")

    tongue_order = ("EN", *TONGUE_ORDER)
    if not 0 <= tongue_id < len(tongue_order):
        raise ActionCompileError("action packet tongue token is unknown")
    try:
        payload_text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ActionCompileError("action packet payload is not valid UTF-8") from error
    if not payload_text.strip():
        raise ActionCompileError("action packet payload is empty")

    packet = ActionPacket(family_byte, method_byte, tongue_id, payload)
    frame = ActionFrame(
        family_token_id=family_token_id,
        method_token_id=method_token_id,
        source_tongue=tongue_order[tongue_id],
        payload=payload_text,
    )
    return packet, frame


def compiler_weight_sha256() -> str:
    return _sha256_json(COMPILER_WEIGHT_MATRIX)


@lru_cache(maxsize=None)
def action_skin(family: str, tongue: str) -> str:
    if family not in TRANSPORT_BYTES:
        raise ActionCompileError(f"unknown action family {family!r}")
    if tongue not in TONGUE_ORDER:
        raise ActionCompileError(f"unknown tongue {tongue!r}")
    return render_tongue(
        tongue,
        TRANSPORT_BYTES[family],
        ca_word_for_opcode,
    )


def _skin_index() -> dict[str, tuple[str, str]]:
    aliases: dict[str, tuple[str, str]] = {}
    for family in FAMILY_ORDER:
        aliases[family] = (family, "EN")
        for tongue in TONGUE_ORDER:
            skin = action_skin(family, tongue)
            if skin in aliases and aliases[skin][0] != family:
                raise RuntimeError(f"action skin collision: {skin!r}")
            aliases[skin] = (family, tongue)
    return aliases


ACTION_SKINS = _skin_index()


@lru_cache(maxsize=None)
def method_skin(family: str, method: str, tongue: str) -> str:
    try:
        byte = METHOD_TRANSPORT_BYTES[family][method]
    except KeyError as error:
        raise ActionCompileError(f"unknown {family!r} method {method!r}") from error
    if tongue not in TONGUE_ORDER:
        raise ActionCompileError(f"unknown tongue {tongue!r}")
    return render_tongue(tongue, byte, ca_word_for_opcode)


@lru_cache(maxsize=None)
def _method_skin_index(family: str) -> dict[str, tuple[str, str]]:
    if family not in METHOD_TRANSPORT_BYTES:
        raise ActionCompileError(f"family {family!r} has no method token table")
    aliases: dict[str, tuple[str, str]] = {}
    for method in METHOD_TRANSPORT_BYTES[family]:
        aliases[method] = (method, "EN")
        for tongue in TONGUE_ORDER:
            skin = method_skin(family, method, tongue)
            old = aliases.get(skin)
            if old is not None and old[0] != method:
                raise RuntimeError(f"{family} method skin collision: {skin!r}")
            aliases[skin] = (method, tongue)
    return aliases


def tokenize_method(family: str, payload: str, default_method: str) -> MethodToken:
    surface, separator, arguments = payload.partition(" :: ")
    if separator:
        source = surface.strip()
        method_payload = arguments.strip()
    else:
        source = default_method
        method_payload = payload.strip()
    if not source or not method_payload:
        raise ActionCompileError(f"{family} method must use METHOD :: PAYLOAD")
    aliases = _method_skin_index(family)
    resolved = aliases.get(source) or aliases.get(source.lower())
    if resolved is None:
        raise ActionCompileError(f"unknown {family} method token {source!r}")
    method, source_tongue = resolved
    order = tuple(METHOD_TRANSPORT_BYTES[family])
    return MethodToken(
        family=family,
        method=method,
        method_id=order.index(method),
        source_token=source,
        source_tongue=source_tongue,
        payload=method_payload,
        transport_byte=METHOD_TRANSPORT_BYTES[family][method],
    )


@lru_cache(maxsize=None)
def _method_weight_matrix(family: str) -> tuple[MethodWeightRow, ...]:
    count = len(METHOD_TRANSPORT_BYTES[family])
    legacy_count = LEGACY_METHOD_COUNTS[family]
    if count < legacy_count:
        raise ActionCompileError("typed method table lost a legacy row")
    legacy = tuple(
        radial_power_weight(index, legacy_count)
        for index in range(legacy_count)
    )
    extension = tuple(
        radial_power_weight(index, count)
        for index in range(legacy_count, count)
    )
    return legacy + extension


def _select_method_weight(token: MethodToken) -> MethodWeightRow:
    table = _method_weight_matrix(token.family)
    one_hot = tuple(int(index == token.method_id) for index in range(len(table)))
    selected_code = sum(bit * row.method_code for bit, row in zip(one_hot, table))
    selected = next((row for row in table if row.method_code == selected_code), None)
    if selected is None:
        raise ActionCompileError("method weight table failed to select one exact row")
    return selected


def method_weight_sha256(family: str) -> str:
    """Seal the complete numeric method bank without relying on class names."""

    if family not in METHOD_TRANSPORT_BYTES:
        raise ActionCompileError(f"family {family!r} has no method token table")
    rows = _method_weight_matrix(family)
    return _sha256_json({
        "family": family,
        "methods": [
            {
                "method_token_id": index,
                "transport_byte": byte,
                "weight_row": rows[index].as_dict(),
            }
            for index, byte in enumerate(METHOD_TRANSPORT_BYTES[family].values())
        ],
    })


def _method_geometry_gate(token: MethodToken, row: MethodWeightRow) -> dict[str, Any]:
    point = (row.trits[0] * 0.25, row.trits[1] * 0.25)
    measurement = quine_seeded_region(point, point, 0.125)
    if measurement["trit"] != -1:
        raise ActionCompileError("method weight lies outside its seeded Klein region")
    return {
        **measurement,
        "point": list(measurement["point"]),
        "seed": list(measurement["seed"]),
        "gate": "inside",
        "radial_phase": [row.phase_numerator, row.phase_denominator],
    }


def tokenize_action(text: str) -> ActionToken:
    if not isinstance(text, str):
        raise TypeError("action input must be text")
    encoded = text.encode("utf-8")
    if not encoded or len(encoded) > MAX_INPUT_BYTES:
        raise ActionCompileError(
            f"action input must contain 1..{MAX_INPUT_BYTES} UTF-8 bytes"
        )
    surface, separator, payload = text.partition(" :: ")
    if not separator or not surface.strip() or not payload.strip():
        raise ActionCompileError("action must use FAMILY :: PAYLOAD")
    source = surface.strip()
    resolved = ACTION_SKINS.get(source) or ACTION_SKINS.get(source.lower())
    if resolved is None:
        raise ActionCompileError(f"unknown action token {source!r}")
    family, source_tongue = resolved
    canonical_payload = payload.strip()
    return ActionToken(
        family=family,
        token_id=FAMILY_ORDER.index(family),
        source_token=source,
        source_tongue=source_tongue,
        payload=canonical_payload,
        transport_byte=TRANSPORT_BYTES[family],
    )


def _select_weight(token: ActionToken) -> CompilerWeightRow:
    one_hot = tuple(int(index == token.token_id) for index in range(len(FAMILY_ORDER)))
    width = len(COMPILER_WEIGHT_MATRIX[0])
    if len(COMPILER_WEIGHT_MATRIX) != len(FAMILY_ORDER) or any(
        len(row) != width for row in COMPILER_WEIGHT_MATRIX
    ):
        raise ActionCompileError("compiler weight matrix shape is invalid")
    selected = tuple(
        sum(one_hot[row] * COMPILER_WEIGHT_MATRIX[row][column] for row in range(len(one_hot)))
        for column in range(width)
    )
    return CompilerWeightRow.decode(selected)


def _geometry_gate(token: ActionToken, row: CompilerWeightRow) -> dict[str, Any]:
    point = (row.trits[0] * 0.25, row.trits[1] * 0.25)
    measurement = quine_seeded_region(
        point,
        GEOMETRY_SEEDS[token.family],
        GEOMETRY_REGION_RADIUS,
    )
    if measurement["trit"] != -1:
        raise ActionCompileError("compiler weight lies outside its Klein action region")
    return {
        **measurement,
        "point": list(measurement["point"]),
        "seed": list(measurement["seed"]),
        "gate": "inside",
    }


@lru_cache(maxsize=None)
def _atomic_packet(family: str, source_tongue: str) -> dict[str, Any]:
    surface_state = map_token_to_atomic_state(
        family,
        language=source_tongue,
        context_class="ACTION",
    )
    action_lexeme = ACTION_CARRIER_LEXEMES[family]
    state = map_token_to_atomic_state(
        action_lexeme,
        language=source_tongue,
        context_class="ACTION",
    )
    return {
        "surface_token": family,
        "surface_semantic_class": surface_state.semantic_class,
        "action_carrier_lexeme": action_lexeme,
        "token": state.token,
        "language": state.language,
        "context_class": state.context_class,
        "semantic_class": state.semantic_class,
        "element": {
            "symbol": state.element.symbol,
            "Z": state.element.Z,
            "group": state.element.group,
            "period": state.element.period,
            "valence": state.element.valence,
            "electronegativity": state.element.electronegativity,
            "witness_stable": state.element.witness_stable,
        },
        "tau": state.tau.as_dict(),
        "negative_state": state.negative_state,
        "dual_state": state.dual_state,
        "band_flag": state.band_flag,
        "resilience": state.resilience,
        "adaptivity": state.adaptivity,
        "trust_baseline": state.trust_baseline,
        "semantic_resolved": state.semantic_resolved,
        "semantic_source": state.semantic_source,
    }


def _byte_slots(canonical_text: str, face: int) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for offset, byte in enumerate(canonical_text.encode("utf-8")):
        slot = Slot(byte >> 4, byte & 0x0F, face)
        packets.append(
            {
                "offset": offset,
                "byte": byte,
                "bits": f"{byte:08b}",
                "address": slot.name,
                "face": slot.face,
                "opposite_face": slot.opposite().face,
                "depth": slot.depth(),
            }
        )
    return packets


def _transport_packet(token: ActionToken) -> dict[str, Any]:
    return {
        "byte": token.transport_byte,
        "bits": f"{token.transport_byte:08b}",
        "forms": {
            tongue: action_skin(token.family, tongue) for tongue in TONGUE_ORDER
        },
    }


@lru_cache(maxsize=None)
def _method_atomic_packet(method: str, source_tongue: str) -> dict[str, Any]:
    state = map_token_to_atomic_state(
        method,
        language=source_tongue,
        context_class="ACTION",
    )
    return {
        "token": state.token,
        "language": state.language,
        "context_class": state.context_class,
        "semantic_class": state.semantic_class,
        "tau": state.tau.as_dict(),
        "negative_state": state.negative_state,
        "dual_state": state.dual_state,
        "band_flag": state.band_flag,
        "semantic_resolved": state.semantic_resolved,
        "semantic_source": state.semantic_source,
    }


def _method_transport_packet(token: MethodToken) -> dict[str, Any]:
    return {
        "byte": token.transport_byte,
        "bits": f"{token.transport_byte:08b}",
        "forms": {
            tongue: method_skin(token.family, token.method, tongue)
            for tongue in TONGUE_ORDER
        },
    }


def _parse_integer(text: str, *, low: int, high: int, name: str) -> int:
    raw = text.strip()
    try:
        if raw.lower().startswith("0x"):
            value = int(raw, 16)
        elif any(char in "abcdefABCDEF" for char in raw):
            value = int(raw, 16)
        else:
            value = int(raw, 10)
    except ValueError as error:
        raise ActionCompileError(f"{name} must be an integer") from error
    if not low <= value <= high:
        raise ActionCompileError(f"{name} must be between {low} and {high}")
    return value


def _opcode_packet(name: str) -> dict[str, Any]:
    byte = _NAME_TO_BYTE[name]
    return {
        "kind": "o64",
        "name": name,
        "byte": byte,
        "bits": f"{byte:08b}",
        "forms": {
            tongue: render_tongue(tongue, byte, ca_word_for_opcode)
            for tongue in TONGUE_ORDER
        },
    }


class ActionExecutor(ABC):
    family: str
    executor_code: int
    sandbox_code: int

    @abstractmethod
    def execute(self, payload: str) -> ExecutionPacket:
        raise NotImplementedError


class ArithmeticAction(ActionExecutor):
    family = "math"
    executor_code = 1
    sandbox_code = 0

    def execute(self, payload: str) -> ExecutionPacket:
        try:
            result = compute(payload)
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise ActionCompileError(f"math compiler rejected payload: {error}") from error
        if result["agree"] is not True:
            raise ActionCompileError("CA result did not agree with the independent oracle")
        native = result.get("native")
        if native is not None and native.get("matches") is not True:
            raise ActionCompileError("native CA program did not match composed execution")
        op_names = tuple(
            item
            for item in result["rpn"]
            if isinstance(item, str) and item in _NAME_TO_BYTE
        )
        lowered = tuple(_opcode_packet(name) for name in op_names)
        return ExecutionPacket(
            value=result["core"],
            speech_value=result["core"],
            lowered_tokens=lowered,
            details={"compiler": "tongues.opcode_compose.compute", **result},
        )


class ActionMethod(ABC):
    family: str
    name: str

    @abstractmethod
    def execute(self, payload: str) -> ExecutionPacket:
        raise NotImplementedError


class RubixMovesMethod(ActionMethod):
    family = "rubix"
    name = "moves"

    def execute(self, payload: str) -> ExecutionPacket:
        try:
            result = run_moves(payload, max_steps=100_000)
        except (ValueError, TypeError, BitSpineError) as error:
            raise ActionCompileError(f"Rubix compiler rejected payload: {error}") from error
        lowered = tuple(
            {
                "kind": "rubix-move",
                "index": row["index"],
                "move": row["move"],
                "face": row["face"],
                "tongue": row["tongue"],
                "instruction": row["instruction"],
                "instruction_name": row["instruction_name"],
                "byte": ord(row["instruction"]),
                "bits": f"{ord(row['instruction']):08b}",
            }
            for row in result["conlang_projection"]
        )
        return ExecutionPacket(result["machine"], True, lowered, result)


class RubixDualMethod(ActionMethod):
    family = "rubix"
    name = "dual"

    def execute(self, payload: str) -> ExecutionPacket:
        face = _parse_integer(payload, low=1, high=6, name="face")
        opposite = dual(face)
        return ExecutionPacket(
            opposite,
            opposite,
            (),
            {"face": face, "opposite_face": opposite, "involution": dual(opposite) == face},
        )


class RubixSlotMethod(ActionMethod):
    family = "rubix"
    name = "slot"

    def execute(self, payload: str) -> ExecutionPacket:
        pieces = payload.split()
        if len(pieces) != 2:
            raise ActionCompileError("rubix slot expects BYTE FACE")
        byte = _parse_integer(pieces[0], low=0, high=255, name="byte")
        face = _parse_integer(pieces[1], low=1, high=6, name="face")
        slot = Slot(byte >> 4, byte & 0x0F, face)
        record = {
            "address": slot.name,
            "byte": slot.byte,
            "bits": f"{slot.byte:08b}",
            "face": slot.face,
            "opposite_face": slot.opposite().face,
            "depth": slot.depth(),
        }
        return ExecutionPacket(record, True, (), record)


class RubixEncodeMethod(ActionMethod):
    family = "rubix"
    name = "encode"

    def execute(self, payload: str) -> ExecutionPacket:
        pieces = payload.split(maxsplit=1)
        if len(pieces) != 2 or not pieces[1]:
            raise ActionCompileError("rubix encode expects FACE TEXT")
        face = _parse_integer(pieces[0], low=1, high=6, name="face")
        text = pieces[1]
        face_map = {index: face for index in range(len(text.encode("utf-8")))}
        slots = to_depth(text, face_map)
        records = [
            {
                "address": slot.name,
                "byte": slot.byte,
                "bits": f"{slot.byte:08b}",
                "face": slot.face,
                "depth": slot.depth(),
            }
            for slot in slots
        ]
        return ExecutionPacket(records, len(records), (), {"text": text, "slots": records})


class RubixDecodeMethod(ActionMethod):
    family = "rubix"
    name = "decode"

    def execute(self, payload: str) -> ExecutionPacket:
        names = tuple(part for part in payload.replace(",", " ").split() if part)
        if not names:
            raise ActionCompileError("rubix decode expects one or more ADDRESS.FACE slots")
        slots: list[Slot] = []
        for name in names:
            address, separator, face_text = name.partition(".")
            if not separator:
                raise ActionCompileError(f"rubix slot {name!r} must use ADDRESS.FACE")
            try:
                i, j = cell(address.lower())
            except (ValueError, KeyError) as error:
                raise ActionCompileError(f"invalid Rubix address {address!r}") from error
            face = _parse_integer(face_text, low=1, high=6, name="face")
            slots.append(Slot(i, j, face))
        text = to_base(slots)
        return ExecutionPacket(text, text, (), {"slots": list(names), "text": text})


class RubixAddressMethod(ActionMethod):
    family = "rubix"
    name = "address"

    def execute(self, payload: str) -> ExecutionPacket:
        byte = _parse_integer(payload, low=0, high=255, name="byte")
        address = byte_to_addr(byte)
        record = {"byte": byte, "bits": f"{byte:08b}", "address": address}
        return ExecutionPacket(address, address, (), record)


class RubixByteMethod(ActionMethod):
    family = "rubix"
    name = "byte"

    def execute(self, payload: str) -> ExecutionPacket:
        address = payload.strip().lower()
        if len(address) != 2:
            raise ActionCompileError("rubix byte expects one two-glyph address")
        try:
            byte = addr_to_byte(address)
        except (ValueError, IndexError) as error:
            raise ActionCompileError(f"invalid Rubix address {address!r}") from error
        if byte_to_addr(byte) != address:
            raise ActionCompileError("Rubix address did not round-trip")
        record = {"address": address, "byte": byte, "bits": f"{byte:08b}"}
        return ExecutionPacket(byte, byte, (), record)


class RubixSlotsMethod(ActionMethod):
    family = "rubix"
    name = "slots"

    def execute(self, payload: str) -> ExecutionPacket:
        face = _parse_integer(payload, low=1, high=6, name="face")
        records = [
            {
                "address": slot.name,
                "byte": slot.byte,
                "bits": f"{slot.byte:08b}",
                "face": slot.face,
                "opposite_face": slot.opposite().face,
            }
            for slot in all_slots()
            if slot.face == face
        ]
        if len(records) != 256:
            raise ActionCompileError("Rubix face did not expose exactly 256 byte slots")
        return ExecutionPacket(records, len(records), (), {"face": face, "slots": records})


class RubixViewsMethod(ActionMethod):
    family = "rubix"
    name = "views"

    def execute(self, payload: str) -> ExecutionPacket:
        pieces = payload.split(maxsplit=2)
        if len(pieces) != 3 or not pieces[2]:
            raise ActionCompileError("rubix views expects COUNT SEED TEXT")
        count = _parse_integer(pieces[0], low=1, high=8, name="count")
        seed = _parse_integer(pieces[1], low=0, high=2**31 - 1, name="seed")
        text = pieces[2]
        if len(text.encode("utf-8")) > 256:
            raise ActionCompileError("rubix views text exceeds 256 bytes")
        views = [
            [
                {
                    "address": slot.name,
                    "byte": slot.byte,
                    "face": slot.face,
                }
                for slot in view
            ]
            for view in stochastic_views(text, count, seed)
        ]
        if any(to_base([Slot(item["byte"] >> 4, item["byte"] & 0x0F, item["face"]) for item in view]) != text for view in views):
            raise ActionCompileError("Rubix stochastic view did not return to base text")
        return ExecutionPacket(
            views,
            len(views),
            (),
            {"count": count, "seed": seed, "text": text, "views": views},
        )


class LoomRouteMethod(ActionMethod):
    family = "loom"
    name = "route"

    def execute(self, payload: str) -> ExecutionPacket:
        pieces = payload.split()
        if len(pieces) not in {2, 3, 4}:
            raise ActionCompileError("loom route expects SOURCE TARGET [TONGUE] [ORIENTATION]")
        try:
            source = Address.parse(pieces[0])
            target = Address.parse(pieces[1])
            tongue = pieces[2].upper() if len(pieces) >= 3 else "CA"
            orientation = pieces[3].lower() if len(pieces) == 4 else "forward"
            result = route(source, target, tongue=tongue, orientation=orientation)
            reverse = reverse_route(result)
            movement = round_trip_movement(result)
        except (ValueError, RuntimeError, AssertionError) as error:
            raise ActionCompileError(f"Loom route rejected payload: {error}") from error
        if not result["arrived"] or movement != 0:
            raise ActionCompileError("Loom route did not arrive with a zero-sum retrace")
        lowered = tuple({"kind": "loom-route-segment", **segment} for segment in result["segments"])
        return ExecutionPacket(
            True,
            True,
            lowered,
            {**result, "reverse": reverse, "round_trip_movement": movement},
        )


class LoomCellMethod(ActionMethod):
    family = "loom"
    name = "cell"

    def execute(self, payload: str) -> ExecutionPacket:
        pieces = payload.split()
        if not 1 <= len(pieces) <= 4:
            raise ActionCompileError("loom cell expects ADDRESS [TONGUE] [FIXED] [CHARGE]")
        try:
            address = Address.parse(pieces[0])
            tongue = pieces[1].upper() if len(pieces) >= 2 else "CA"
            fixed = bool(_parse_integer(pieces[2], low=0, high=1, name="fixed")) if len(pieces) >= 3 else False
            charge = _parse_integer(pieces[3], low=-1, high=1, name="charge") if len(pieces) == 4 else 1
            if charge == 0:
                raise ActionCompileError("charge must be -1 or +1")
            result = cell_record(address, tongue=tongue, fixed=fixed, charge=charge)
        except (KeyError, ValueError, AssertionError) as error:
            raise ActionCompileError(f"Loom cell rejected payload: {error}") from error
        return ExecutionPacket(result, True, (), result)


class LoomTonguesMethod(ActionMethod):
    family = "loom"
    name = "tongues"

    def execute(self, payload: str) -> ExecutionPacket:
        opcode = _parse_integer(payload, low=0, high=63, name="opcode")
        try:
            forms = tongue_forms(opcode)
        except (ValueError, AssertionError) as error:
            raise ActionCompileError(f"Loom tongue projection failed: {error}") from error
        return ExecutionPacket(forms, len(forms), (), {"opcode": opcode, "forms": forms})


class LoomRadialMethod(ActionMethod):
    family = "loom"
    name = "radial"

    def execute(self, payload: str) -> ExecutionPacket:
        pieces = payload.split()
        if not 2 <= len(pieces) <= 4:
            raise ActionCompileError("loom radial expects OPCODE TONGUE [ORIENTATION] [CHARGE]")
        opcode = _parse_integer(pieces[0], low=0, high=63, name="opcode")
        tongue = pieces[1].upper()
        orientation = pieces[2].lower() if len(pieces) >= 3 else "forward"
        charge = _parse_integer(pieces[3], low=-1, high=1, name="charge") if len(pieces) == 4 else 1
        if charge == 0:
            raise ActionCompileError("charge must be -1 or +1")
        try:
            result = radial_phone_coordinate(opcode, tongue, orientation, charge)
        except ValueError as error:
            raise ActionCompileError(f"Loom radial projection failed: {error}") from error
        return ExecutionPacket(result, True, (), result)


class LoomEntityMethod(ActionMethod):
    family = "loom"
    name = "entity"

    def execute(self, payload: str) -> ExecutionPacket:
        pieces = payload.split()
        if len(pieces) not in {1, 2}:
            raise ActionCompileError("loom entity expects ENTITY_ID [TAPE_BITS]")
        tape = pieces[1] if len(pieces) == 2 else "1110"
        try:
            result = run_entity_core(pieces[0], tape)
        except (ValueError, RuntimeError) as error:
            raise ActionCompileError(f"Loom entity rejected payload: {error}") from error
        if not result["halted"]:
            raise ActionCompileError("Loom entity core did not halt")
        return ExecutionPacket(result, True, (), result)


class LoomXYZMethod(ActionMethod):
    family = "loom"
    name = "xyz"

    def execute(self, payload: str) -> ExecutionPacket:
        opcode = _parse_integer(payload, low=0, high=63, name="opcode")
        xyz = opcode_xyz(opcode)
        record = {"opcode": opcode, "xyz": list(xyz)}
        return ExecutionPacket(list(xyz), True, (), record)


class LoomShortestMethod(ActionMethod):
    family = "loom"
    name = "shortest"

    def execute(self, payload: str) -> ExecutionPacket:
        pieces = payload.split()
        if len(pieces) != 2:
            raise ActionCompileError("loom shortest expects START TARGET")
        start = _parse_integer(pieces[0], low=0, high=63, name="start")
        target = _parse_integer(pieces[1], low=0, high=63, name="target")
        try:
            path = shortest_cell_route(start, target)
        except RuntimeError as error:
            raise ActionCompileError(f"Loom shortest route failed: {error}") from error
        edges = [
            {
                "left": left,
                "right": right,
                "wall_id": wall.wall_id,
                "wall_kind": wall.kind,
                "wall_density": wall.density,
            }
            for left, right, wall in path
        ]
        return ExecutionPacket(
            edges,
            len(edges),
            (),
            {"start": start, "target": target, "edges": edges},
        )


class LoomRenewalMethod(ActionMethod):
    family = "loom"
    name = "renewal"

    def execute(self, payload: str) -> ExecutionPacket:
        state = payload.strip()
        try:
            successors = renewal_successors(state)
        except ValueError as error:
            raise ActionCompileError(f"Loom renewal rejected payload: {error}") from error
        record = {"state": state, "successors": list(successors)}
        return ExecutionPacket(list(successors), len(successors), (), record)


class LoomBindMethod(ActionMethod):
    family = "loom"
    name = "bind"

    def execute(self, payload: str) -> ExecutionPacket:
        pieces = payload.split()
        if len(pieces) != 2:
            raise ActionCompileError("loom bind expects OUTER INNER")
        try:
            bound = bind_renewal(pieces[0], pieces[1])
        except ValueError as error:
            raise ActionCompileError(f"Loom bind rejected payload: {error}") from error
        record = {"outer": pieces[0], "inner": pieces[1], "bound": bound}
        return ExecutionPacket(bound, bound, (), record)


class LoomCrossDayMethod(ActionMethod):
    family = "loom"
    name = "cross_day"

    def execute(self, payload: str) -> ExecutionPacket:
        pieces = payload.split()
        if len(pieces) != 2:
            raise ActionCompileError("loom cross_day expects DAY BOUND_STATE")
        day = _parse_integer(pieces[0], low=0, high=2**31 - 2, name="day")
        try:
            next_day, state = cross_day(day, pieces[1])
        except ValueError as error:
            raise ActionCompileError(f"Loom day crossing rejected payload: {error}") from error
        record = {"day": day, "bound": pieces[1], "next_day": next_day, "state": state}
        return ExecutionPacket(record, next_day, (), record)


class LoomDomainMethod(ActionMethod):
    family = "loom"
    name = "domain"

    def execute(self, payload: str) -> ExecutionPacket:
        try:
            address = Address.parse(payload)
            record = address_domain(address).as_record()
        except ValueError as error:
            raise ActionCompileError(f"Loom domain rejected payload: {error}") from error
        record = {"address": str(address), **record}
        return ExecutionPacket(record, True, (), record)


class LoomWallsMethod(ActionMethod):
    family = "loom"
    name = "walls"

    def execute(self, payload: str) -> ExecutionPacket:
        try:
            address = Address.parse(payload)
            walls = cube_walls(address)
        except ValueError as error:
            raise ActionCompileError(f"Loom walls rejected payload: {error}") from error
        records = [
            {
                "wall_id": wall.wall_id,
                "kind": wall.kind,
                "density": wall.density,
                "member_opcodes": list(wall.member_opcodes),
                "members": [str(member) for member in wall.members],
            }
            for wall in walls
        ]
        return ExecutionPacket(
            records,
            len(records),
            (),
            {"address": str(address), "walls": records},
        )


class LoomChildrenMethod(ActionMethod):
    family = "loom"
    name = "children"

    def execute(self, payload: str) -> ExecutionPacket:
        try:
            address = Address.parse(payload)
            records = [str(child) for child in children(address)]
        except ValueError as error:
            raise ActionCompileError(f"Loom children rejected payload: {error}") from error
        if len(records) != 64:
            raise ActionCompileError("Loom address did not expose exactly 64 children")
        return ExecutionPacket(
            records,
            len(records),
            (),
            {"address": str(address), "children": records},
        )


class MethodDispatchAction(ActionExecutor):
    default_method: str
    methods: tuple[ActionMethod, ...]

    def execute(self, payload: str) -> ExecutionPacket:
        token = tokenize_method(self.family, payload, self.default_method)
        row = _select_method_weight(token)
        expected_order = tuple(METHOD_TRANSPORT_BYTES[self.family])
        actual_order = tuple(method.name for method in self.methods)
        if actual_order != expected_order:
            raise ActionCompileError("method class registry and token table disagree")
        method = self.methods[row.method_code - 1]
        if method.family != self.family or method.name != token.method:
            raise ActionCompileError("method weight and class registry disagree")
        geometry = _method_geometry_gate(token, row)
        packet = method.execute(token.payload)
        method_token = {
            "kind": "action-method",
            "family": token.family,
            "method": token.method,
            "method_id": token.method_id,
            "source_token": token.source_token,
            "source_tongue": token.source_tongue,
            "transport": _method_transport_packet(token),
            "atomic": _method_atomic_packet(token.method, token.source_tongue),
        }
        method_compiler = {
            "method": token.method,
            "canonical_payload": f"{token.method} :: {token.payload}",
            "weight_row": row.as_dict(),
            "geometry": geometry,
        }
        if token.method_id >= LEGACY_METHOD_COUNTS[self.family]:
            method_compiler["extension_bank_sha256"] = method_weight_sha256(
                self.family
            )
        return ExecutionPacket(
            packet.value,
            packet.speech_value,
            (method_token, *packet.lowered_tokens),
            {
                **packet.details,
                "method_compiler": method_compiler,
            },
        )


class RubixAction(MethodDispatchAction):
    family = "rubix"
    executor_code = 2
    sandbox_code = 0
    default_method = "moves"
    methods = (
        RubixMovesMethod(),
        RubixDualMethod(),
        RubixSlotMethod(),
        RubixEncodeMethod(),
        RubixDecodeMethod(),
        RubixAddressMethod(),
        RubixByteMethod(),
        RubixSlotsMethod(),
        RubixViewsMethod(),
    )


class LoomAction(MethodDispatchAction):
    family = "loom"
    executor_code = 4
    sandbox_code = 0
    default_method = "route"
    methods = (
        LoomRouteMethod(),
        LoomCellMethod(),
        LoomTonguesMethod(),
        LoomRadialMethod(),
        LoomEntityMethod(),
        LoomXYZMethod(),
        LoomShortestMethod(),
        LoomRenewalMethod(),
        LoomBindMethod(),
        LoomCrossDayMethod(),
        LoomDomainMethod(),
        LoomWallsMethod(),
        LoomChildrenMethod(),
    )


class ToolSealAction(ActionExecutor):
    family = "tool"
    executor_code = 3
    sandbox_code = 1

    def execute(self, payload: str) -> ExecutionPacket:
        seal = static_seal([payload])
        canonical_receipts: list[dict[str, Any]] = []
        for receipt in seal["receipts"]:
            normalized = dict(receipt)
            if "handler" in normalized:
                normalized["handler"] = Path(normalized["handler"]).name
            canonical_receipts.append(normalized)
        canonical_seal = {**seal, "receipts": canonical_receipts}
        if not canonical_seal["all_valid"]:
            reason = canonical_receipts[0].get("reason", "invalid tool call")
            raise ActionCompileError(f"tool static seal rejected payload: {reason}")
        call = canonical_receipts[0]["call"]
        call_bytes = payload.encode("utf-8")
        lowered = (
            {
                "kind": "tool-call",
                "tool": call["tool"],
                "payload": call["payload"],
                "sha256": hashlib.sha256(call_bytes).hexdigest(),
                "bytes": len(call_bytes),
            },
        )
        return ExecutionPacket(
            value=True,
            speech_value=True,
            lowered_tokens=lowered,
            details={
                "sandbox": "static_only",
                "dispatched": False,
                "seal": canonical_seal,
            },
        )


EXECUTORS: dict[int, ActionExecutor] = {
    executor.executor_code: executor
    for executor in (ArithmeticAction(), RubixAction(), ToolSealAction(), LoomAction())
}


class ActionCompiler:
    """Compile one bounded action and return a deterministic sealed receipt."""

    def compile(self, text: str) -> dict[str, Any]:
        token = tokenize_action(text)
        row = _select_weight(token)
        executor = EXECUTORS.get(row.executor_code)
        if executor is None:
            raise ActionCompileError("compiler weight selected an unknown executor")
        if executor.family != token.family:
            raise ActionCompileError("compiler weight and canonical family disagree")
        if executor.sandbox_code != row.sandbox_code:
            raise ActionCompileError("compiler weight and sandbox contract disagree")
        geometry = _geometry_gate(token, row)
        atomic = _atomic_packet(token.family, token.source_tongue)
        if atomic["semantic_class"] != "ACTION":
            raise ActionCompileError("root token did not resolve to atomic ACTION")

        packet = executor.execute(token.payload)
        spoken, fingerprint, observed = speak(lambda: packet.speech_value, ())
        if observed["raised"]:
            raise ActionCompileError("speech observation unexpectedly raised")
        method_compiler = packet.details.get("method_compiler", {})
        canonical_payload = method_compiler.get("canonical_payload", token.payload)
        canonical_text = f"{token.family} :: {canonical_payload}"
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "input": {
                "source_token": token.source_token,
                "source_tongue": token.source_tongue,
                "canonical": canonical_text,
                "family": token.family,
                "payload": canonical_payload,
                "source_payload": token.payload,
            },
            "action_token": {
                "token_id": token.token_id,
                "transport": _transport_packet(token),
                "atomic": atomic,
            },
            "compiler": {
                "weight_sha256": compiler_weight_sha256(),
                "weight_row": row.as_dict(),
                "executor": type(executor).__name__,
                "geometry": geometry,
                "sandbox": "static_only" if row.sandbox_code else "pure_local",
            },
            "representation": {
                "byte_slots": _byte_slots(canonical_text, row.face),
                "lowered_tokens": list(packet.lowered_tokens),
            },
            "execution": {
                "value": packet.value,
                "details": packet.details,
            },
            "speech": {
                "blocks": spoken,
                "fingerprint": fingerprint,
                "observed": observed,
            },
        }
        return {**body, "receipt_sha256": _sha256_json(body)}

    def compile_frame(self, frame: ActionFrame) -> dict[str, Any]:
        """Compile a compact tokenizer frame into an action packet.

        This is Clay's throughput path.  It retains the independent weight,
        geometry, class-registry, executor, and sandbox checks, but does not
        build the multilingual audit projections and per-byte display slots.
        Use ``compile`` when those expanded witnesses are required.
        """

        return self._compile_frame(frame, compiler_weight_sha256())

    def compile_packet(self, encoded: bytes) -> dict[str, Any]:
        """Compile a packet and retain independently replayable packet evidence."""

        packet, frame = decode_action_packet(encoded)
        action_receipt = self._compile_frame(frame, compiler_weight_sha256())
        body = {
            "schema": ACTION_PACKET_SCHEMA,
            "packet": {
                "family_transport_byte": packet.family_transport_byte,
                "method_transport_byte": packet.method_transport_byte,
                "source_tongue_id": packet.source_tongue_id,
                "payload_byte_count": len(packet.payload),
                "encoded_hex": encoded.hex(),
                "packet_sha256": hashlib.sha256(encoded).hexdigest(),
            },
            "action_receipt_sha256": action_receipt["receipt_sha256"],
            "action": action_receipt,
        }
        return {**body, "receipt_sha256": _sha256_json(body)}

    def compile_packet_fast(self, encoded: bytes) -> dict[str, Any]:
        """Compile a byte-token packet without the optional outer audit package.

        CRC and every registry check still run. The returned action receipt is
        identical to compiling the decoded ActionFrame directly and retains its
        execution/speech SHA-256 seal. Use :meth:`compile_packet` when the raw
        transport packet must also remain independently replayable.
        """

        _, frame = decode_action_packet(encoded)
        return self._compile_frame(frame, compiler_weight_sha256())

    def _compile_frame(
        self,
        frame: ActionFrame,
        weight_sha256: str,
    ) -> dict[str, Any]:
        """Compile one frame against a tape-scoped immutable weight digest."""

        if not isinstance(frame, ActionFrame):
            raise TypeError("compile_frame expects an ActionFrame")
        if not 0 <= frame.family_token_id < len(FAMILY_ORDER):
            raise ActionCompileError("family token id is outside the compiler table")
        if frame.source_tongue not in ("EN", *TONGUE_ORDER):
            raise ActionCompileError("source tongue is outside the six-tongue table")
        if not isinstance(frame.payload, str) or not frame.payload.strip():
            raise ActionCompileError("action frame payload must be non-empty text")
        if len(frame.payload.encode("utf-8")) > MAX_INPUT_BYTES:
            raise ActionCompileError("action frame payload exceeds the byte limit")

        family = FAMILY_ORDER[frame.family_token_id]
        payload = frame.payload.strip()
        method_name: str | None = None
        effective_method_id: int | None = None
        if family in METHOD_TRANSPORT_BYTES:
            methods = tuple(METHOD_TRANSPORT_BYTES[family])
            method_id = 0 if frame.method_token_id is None else frame.method_token_id
            if not 0 <= method_id < len(methods):
                raise ActionCompileError("method token id is outside the family table")
            effective_method_id = method_id
            method_name = methods[method_id]
            payload = f"{method_name} :: {payload}"
        elif frame.method_token_id is not None:
            raise ActionCompileError("this family does not accept a method token")

        token = ActionToken(
            family=family,
            token_id=frame.family_token_id,
            source_token=family if frame.source_tongue == "EN" else action_skin(family, frame.source_tongue),
            source_tongue=frame.source_tongue,
            payload=payload,
            transport_byte=TRANSPORT_BYTES[family],
        )
        row = _select_weight(token)
        executor = EXECUTORS.get(row.executor_code)
        if executor is None or executor.family != family:
            raise ActionCompileError("compiler weight and action frame disagree")
        if executor.sandbox_code != row.sandbox_code:
            raise ActionCompileError("compiler weight and sandbox contract disagree")
        geometry = _geometry_gate(token, row)
        packet = executor.execute(token.payload)
        speech_program = compile_observation(
            {"value": packet.speech_value, "raised": False}
        )
        method_compiler = packet.details.get("method_compiler", {})
        body = {
            "schema": "clay.action-frame.v1",
            "frame": {
                "family_token_id": frame.family_token_id,
                "family": family,
                "method_token_id": effective_method_id,
                "method": method_name,
                "source_tongue": frame.source_tongue,
                "payload": frame.payload.strip(),
            },
            "compiler": {
                "weight_sha256": weight_sha256,
                "weight_row": row.as_dict(),
                "executor": type(executor).__name__,
                "geometry": geometry,
                "method_compiler": method_compiler or None,
                "sandbox": "static_only" if row.sandbox_code else "pure_local",
            },
            "execution": {
                "value": packet.value,
                "details": packet.details,
            },
            "speech_program": speech_program,
        }
        return {**body, "receipt_sha256": _sha256_json(body)}

    @staticmethod
    def _validate_tape(tape: ActionTape) -> None:
        if not isinstance(tape, ActionTape):
            raise TypeError("compile_tape expects an ActionTape")
        if not tape.frames:
            raise ActionCompileError("action tape must contain at least one frame")
        if len(tape.frames) > MAX_TAPE_FRAMES:
            raise ActionCompileError("action tape exceeds the frame limit")
        if not all(isinstance(frame, ActionFrame) for frame in tape.frames):
            raise TypeError("action tape may contain only ActionFrame values")

    def _compile_tape_body(
        self,
        tape: ActionTape,
        *,
        seal_scope: str,
    ) -> dict[str, Any]:
        self._validate_tape(tape)
        weight_sha256 = compiler_weight_sha256()
        actions = [
            self._compile_frame(frame, weight_sha256)
            for frame in tape.frames
        ]
        if compiler_weight_sha256() != weight_sha256:
            raise ActionCompileError("compiler weight changed during tape compilation")
        speech_steps = [
            {
                "step": index,
                "family_token_id": action["frame"]["family_token_id"],
                "method_token_id": action["frame"]["method_token_id"],
                "active_token_ids": action["speech_program"]["active_token_ids"],
                "active_opcodes": action["speech_program"]["active_opcodes"],
                "bit_vector": action["speech_program"]["bit_vector"],
                "trit_vector": action["speech_program"]["trit_vector"],
            }
            for index, action in enumerate(actions)
        ]
        return {
            "schema": TAPE_SCHEMA,
            "receipt_seal_scope": seal_scope,
            "frame_count": len(actions),
            "compiler_weight_sha256": weight_sha256,
            "action_receipt_sha256": [
                action["receipt_sha256"] for action in actions
            ],
            "actions": actions,
            "speech_tape": {
                "schema": "clay.speech-block-tape.v1",
                "steps": speech_steps,
                "opcode_stream": [
                    opcode
                    for step in speech_steps
                    for opcode in step["active_opcodes"]
                ],
            },
        }

    @staticmethod
    def _tape_chain_payload(body: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema": TAPE_SEAL_SCHEMA,
            "tape_schema": body["schema"],
            "receipt_seal_scope": body["receipt_seal_scope"],
            "frame_count": body["frame_count"],
            "compiler_weight_sha256": body["compiler_weight_sha256"],
            "action_receipt_sha256": body["action_receipt_sha256"],
            "speech_tape": body["speech_tape"],
        }

    def compile_tape(self, tape: ActionTape) -> dict[str, Any]:
        """Compile an ordered token tape into actions and grounded speech.

        Every frame crosses the same weight, geometry, class-registry,
        executor, and sandbox boundaries as :meth:`compile_frame`.  The layer
        is fail closed: a malformed frame raises before a tape receipt exists.
        All currently registered executors are pure local computations or the
        non-dispatching static tool seal, so no external side effect can be
        partially committed by a rejected tape.
        """

        body = self._compile_tape_body(
            tape,
            seal_scope="ordered-child-receipts+speech-tape",
        )
        return {
            **body,
            "receipt_sha256": _sha256_json(self._tape_chain_payload(body)),
        }

    def _compile_tape_full_body_reference(
        self,
        tape: ActionTape,
    ) -> dict[str, Any]:
        """Matched benchmark control using the former nested-body seal."""

        body = self._compile_tape_body(tape, seal_scope="full-nested-body")
        return {**body, "receipt_sha256": _sha256_json(body)}


def verify_action_packet_receipt(receipt: dict[str, Any]) -> bool:
    """Independently replay a byte packet and its compiled action receipt."""

    if not isinstance(receipt, dict) or receipt.get("schema") != ACTION_PACKET_SCHEMA:
        return False
    packet_record = receipt.get("packet")
    if not isinstance(packet_record, dict):
        return False
    try:
        encoded = bytes.fromhex(packet_record["encoded_hex"])
        packet, frame = decode_action_packet(encoded)
        replay = ActionCompiler().compile_frame(frame)
    except (KeyError, TypeError, ValueError, ActionCompileError):
        return False
    expected_packet = {
        "family_transport_byte": packet.family_transport_byte,
        "method_transport_byte": packet.method_transport_byte,
        "source_tongue_id": packet.source_tongue_id,
        "payload_byte_count": len(packet.payload),
        "encoded_hex": encoded.hex(),
        "packet_sha256": hashlib.sha256(encoded).hexdigest(),
    }
    if packet_record != expected_packet:
        return False
    if receipt.get("action") != replay:
        return False
    if receipt.get("action_receipt_sha256") != replay["receipt_sha256"]:
        return False
    body = dict(receipt)
    digest = body.pop("receipt_sha256", None)
    return isinstance(digest, str) and _sha256_json(body) == digest


def verify_action_tape_receipt(receipt: dict[str, Any]) -> bool:
    """Verify every child seal, speech boundary, and the outer chain seal."""

    if not isinstance(receipt, dict) or receipt.get("schema") != TAPE_SCHEMA:
        return False
    if receipt.get("receipt_seal_scope") != "ordered-child-receipts+speech-tape":
        return False
    weight_sha256 = receipt.get("compiler_weight_sha256")
    if weight_sha256 != compiler_weight_sha256():
        return False
    actions = receipt.get("actions")
    if not isinstance(actions, list) or not actions:
        return False
    if receipt.get("frame_count") != len(actions) or len(actions) > MAX_TAPE_FRAMES:
        return False
    child_hashes: list[str] = []
    speech_steps: list[dict[str, Any]] = []
    for index, action in enumerate(actions):
        if not isinstance(action, dict) or "receipt_sha256" not in action:
            return False
        try:
            if action["compiler"]["weight_sha256"] != weight_sha256:
                return False
        except (KeyError, TypeError):
            return False
        child_body = dict(action)
        child_digest = child_body.pop("receipt_sha256")
        if not isinstance(child_digest, str) or _sha256_json(child_body) != child_digest:
            return False
        child_hashes.append(child_digest)
        try:
            speech_steps.append({
                "step": index,
                "family_token_id": action["frame"]["family_token_id"],
                "method_token_id": action["frame"]["method_token_id"],
                "active_token_ids": action["speech_program"]["active_token_ids"],
                "active_opcodes": action["speech_program"]["active_opcodes"],
                "bit_vector": action["speech_program"]["bit_vector"],
                "trit_vector": action["speech_program"]["trit_vector"],
            })
        except (KeyError, TypeError):
            return False
    expected_speech_tape = {
        "schema": "clay.speech-block-tape.v1",
        "steps": speech_steps,
        "opcode_stream": [
            opcode
            for step in speech_steps
            for opcode in step["active_opcodes"]
        ],
    }
    if receipt.get("action_receipt_sha256") != child_hashes:
        return False
    if receipt.get("speech_tape") != expected_speech_tape:
        return False
    body = dict(receipt)
    digest = body.pop("receipt_sha256", None)
    return (
        isinstance(digest, str)
        and _sha256_json(ActionCompiler._tape_chain_payload(body)) == digest
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="+", help="FAMILY :: PAYLOAD")
    parser.add_argument("--compact", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    text = " ".join(args.action)
    try:
        receipt = ActionCompiler().compile(text)
    except ActionCompileError as error:
        print(_canonical_json({"accepted": False, "error": str(error)}))
        return 2
    if args.compact:
        print(_canonical_json(receipt))
    else:
        print(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

