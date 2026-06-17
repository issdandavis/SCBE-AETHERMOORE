"""
Cassisivadan (CA) 64-op trit table.

This is the first concrete Sacred Tongue opcode table wired into the canonical
Python atomic/fusion runtime. It exposes deterministic O(1) lookup for CA
operations and adapts the table into the existing AtomicTokenState model so the
same fusion, reducer, and drift code can operate on opcode packets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence

import numpy as np

from .atomic_tokenization import AtomicTokenState, DualState, Element, TritVector
from .chemical_fusion import FusionParams, FusionResult, fuse_atomic_states


KO, AV, RU, CA, UM, DR = 0, 1, 2, 3, 4, 5
TONGUE_ID_CA = 3

BAND_NAMES = {0: "Ctrl", 1: "Data", 2: "Ops", 3: "Mod"}


@dataclass(frozen=True, slots=True)
class CAOpcodeEntry:
    op_id: int
    name: str
    trit: np.ndarray
    feat: np.ndarray


ARITHMETIC = [
    (0x00, "add", [0, 0, 0, +1, 0, 0], [0, 1, 1, 2, 0.1, 2, 3, 0]),
    (0x01, "sub", [0, 0, 0, +1, 0, 0], [1, 1, 1, 2, 0.1, 2, 3, 0]),
    (0x02, "mul", [0, 0, 0, +1, 0, 0], [2, 1, 1, 2, 0.2, 2, 3, 0]),
    (0x03, "div", [0, 0, 0, +1, 0, -1], [3, 1, 1, 2, 0.8, 2, 3, 0]),
    (0x04, "mod", [0, 0, 0, +1, 0, 0], [4, 1, 1, 2, 0.5, 2, 3, 0]),
    (0x05, "pow", [0, 0, 0, +1, 0, +1], [5, 1, 2, 2, 1.2, 2, 3, 0]),
    (0x06, "sqrt", [0, 0, 0, +1, 0, +1], [6, 1, 2, 1, 0.5, 2, 3, 0]),
    (0x07, "log", [0, 0, 0, +1, 0, +1], [7, 1, 2, 1, 0.8, 2, 3, 0]),
    (0x08, "exp", [0, 0, 0, +1, 0, +1], [8, 1, 2, 1, 1.5, 2, 3, 0]),
    (0x09, "abs", [0, 0, 0, +1, 0, 0], [9, 1, 1, 1, 0.0, 2, 3, 0]),
    (0x0A, "neg", [0, 0, 0, +1, 0, 0], [10, 1, 1, 1, 0.1, 2, 3, 0]),
    (0x0B, "inc", [0, 0, 0, +1, 0, 0], [11, 1, 1, 1, 0.1, 2, 3, 0]),
    (0x0C, "dec", [0, 0, 0, +1, 0, 0], [12, 1, 1, 1, 0.1, 2, 3, 0]),
    (0x0D, "floor", [0, 0, 0, +1, 0, -1], [13, 1, 1, 1, 0.2, 2, 3, 0]),
    (0x0E, "ceil", [0, 0, 0, +1, 0, -1], [14, 1, 1, 1, 0.2, 2, 3, 0]),
    (0x0F, "round", [0, 0, 0, +1, 0, -1], [15, 1, 1, 1, 0.2, 2, 3, 0]),
]

LOGIC = [
    (0x10, "and", [+1, 0, 0, +1, 0, 0], [16, 2, 1, 2, 0.1, 2, 3, 0]),
    (0x11, "or", [+1, 0, 0, +1, 0, 0], [17, 2, 1, 2, 0.1, 2, 3, 0]),
    (0x12, "not", [+1, 0, 0, +1, 0, 0], [18, 2, 1, 1, 0.1, 2, 3, 0]),
    (0x13, "xor", [0, 0, 0, +1, +1, 0], [19, 2, 1, 2, 0.3, 2, 3, 0]),
    (0x14, "nand", [+1, 0, 0, +1, 0, 0], [20, 2, 1, 2, 0.2, 2, 3, 0]),
    (0x15, "nor", [+1, 0, 0, +1, 0, 0], [21, 2, 1, 2, 0.2, 2, 3, 0]),
    (0x16, "shl", [0, 0, 0, +1, +1, 0], [22, 2, 1, 2, 0.6, 2, 3, 0]),
    (0x17, "shr", [0, 0, 0, +1, +1, 0], [23, 2, 1, 2, 0.6, 2, 3, 0]),
    (0x18, "rotl", [0, 0, 0, +1, +1, +1], [24, 2, 2, 2, 0.4, 2, 3, 0]),
    (0x19, "rotr", [0, 0, 0, +1, +1, +1], [25, 2, 2, 2, 0.4, 2, 3, 0]),
    (0x1A, "popcount", [0, +1, 0, +1, 0, 0], [26, 2, 2, 1, 0.1, 2, 3, 0]),
    (0x1B, "clz", [0, +1, 0, +1, 0, 0], [27, 2, 2, 1, 0.1, 2, 3, 0]),
    (0x1C, "ctz", [0, +1, 0, +1, 0, 0], [28, 2, 2, 1, 0.1, 2, 3, 0]),
    (0x1D, "bitmask", [0, 0, +1, +1, +1, 0], [29, 2, 2, 2, 0.7, 2, 3, 0]),
    (0x1E, "bitset", [0, 0, 0, +1, 0, 0], [30, 2, 1, 2, 0.3, 2, 3, 0]),
    (0x1F, "bitclear", [0, 0, 0, +1, 0, -1], [31, 2, 1, 2, 0.3, 2, 3, 0]),
]

COMPARISON = [
    (0x20, "eq", [+1, 0, 0, +1, 0, 0], [32, 3, 1, 2, 0.0, 1, 3, 0]),
    (0x21, "neq", [+1, 0, 0, +1, 0, 0], [33, 3, 1, 2, 0.0, 1, 3, 0]),
    (0x22, "lt", [+1, 0, 0, +1, 0, 0], [34, 3, 1, 2, 0.0, 1, 3, 0]),
    (0x23, "lte", [+1, 0, 0, +1, 0, 0], [35, 3, 1, 2, 0.0, 1, 3, 0]),
    (0x24, "gt", [+1, 0, 0, +1, 0, 0], [36, 3, 1, 2, 0.0, 1, 3, 0]),
    (0x25, "gte", [+1, 0, 0, +1, 0, 0], [37, 3, 1, 2, 0.0, 1, 3, 0]),
    (0x26, "cmp", [+1, +1, 0, +1, 0, 0], [38, 3, 1, 2, 0.0, 1, 3, 0]),
    (0x27, "min", [0, 0, 0, +1, 0, 0], [39, 3, 1, 2, 0.0, 1, 3, 0]),
    (0x28, "max", [0, 0, 0, +1, 0, 0], [40, 3, 1, 2, 0.0, 1, 3, 0]),
    (0x29, "clamp", [0, 0, +1, +1, 0, 0], [41, 3, 2, 3, 0.1, 1, 3, 0]),
    (0x2A, "within", [+1, 0, +1, +1, 0, 0], [42, 3, 2, 3, 0.1, 1, 3, 0]),
    (0x2B, "isnan", [0, +1, 0, +1, +1, 0], [43, 3, 1, 1, 0.5, 1, 3, 0]),
    (0x2C, "isinf", [0, +1, 0, +1, +1, 0], [44, 3, 1, 1, 0.5, 1, 3, 0]),
    (0x2D, "isfinite", [0, +1, 0, +1, +1, 0], [45, 3, 1, 1, 0.3, 1, 3, 0]),
    (0x2E, "sign", [0, +1, 0, +1, 0, 0], [46, 3, 1, 1, 0.0, 1, 3, 0]),
    (0x2F, "classify", [0, +1, 0, +1, 0, +1], [47, 3, 2, 1, 0.2, 1, 3, 0]),
]

AGGREGATION = [
    (0x30, "sum", [0, 0, +1, +1, 0, 0], [48, 4, 2, 1, 0.1, 3, 3, 0]),
    (0x31, "product", [0, 0, +1, +1, 0, 0], [49, 4, 2, 1, 0.5, 3, 3, 0]),
    (0x32, "mean", [0, 0, +1, +1, 0, 0], [50, 4, 2, 1, 0.2, 3, 3, 0]),
    (0x33, "variance", [0, 0, +1, +1, 0, 0], [51, 4, 3, 1, 0.3, 3, 3, 0]),
    (0x34, "stdev", [0, 0, +1, +1, 0, 0], [52, 4, 3, 1, 0.3, 3, 3, 0]),
    (0x35, "reduce", [+1, 0, +1, +1, 0, +1], [53, 4, 3, 2, 0.6, 3, 3, 0]),
    (0x36, "fold", [+1, 0, +1, +1, 0, +1], [54, 4, 3, 2, 0.6, 3, 3, 0]),
    (0x37, "scan", [+1, +1, +1, +1, 0, +1], [55, 4, 3, 2, 0.5, 3, 3, 0]),
    (0x38, "filter", [+1, 0, +1, +1, 0, -1], [56, 4, 2, 2, 0.3, 3, 3, 0]),
    (0x39, "map", [0, 0, +1, +1, 0, +1], [57, 4, 2, 2, 0.2, 3, 3, 0]),
    (0x3A, "zip", [0, +1, +1, +1, 0, +1], [58, 4, 2, 2, 0.2, 3, 3, 0]),
    (0x3B, "unzip", [0, +1, +1, +1, 0, -1], [59, 4, 2, 2, 0.3, 3, 3, 0]),
    (0x3C, "sort", [0, 0, +1, +1, 0, +1], [60, 4, 2, 1, 0.2, 3, 3, 0]),
    (0x3D, "unique", [0, 0, +1, +1, 0, -1], [61, 4, 2, 1, 0.3, 3, 3, 0]),
    (0x3E, "count", [0, +1, +1, +1, 0, 0], [62, 4, 2, 1, 0.0, 3, 3, 0]),
    (0x3F, "accum", [0, 0, +1, +1, 0, 0], [63, 4, 3, 2, 0.4, 3, 3, 0]),
]

ALL_OPS = ARITHMETIC + LOGIC + COMPARISON + AGGREGATION

OP_TABLE: Dict[int, CAOpcodeEntry] = {
    op_id: CAOpcodeEntry(
        op_id=op_id,
        name=name,
        trit=np.array(trit, dtype=np.int8),
        feat=np.array(feat, dtype=np.float32),
    )
    for op_id, name, trit, feat in ALL_OPS
}

TRIT_MATRIX = np.array([entry.trit for entry in OP_TABLE.values()], dtype=np.int8)
FEAT_MATRIX = np.array([entry.feat for entry in OP_TABLE.values()], dtype=np.float32)
NAMES = [entry.name for entry in OP_TABLE.values()]


def validate_ca_table() -> tuple[bool, list[str]]:
    errors: list[str] = []
    if len(ALL_OPS) != 64:
        errors.append(f"Expected 64 ops, got {len(ALL_OPS)}")

    ids = [op[0] for op in ALL_OPS]
    if sorted(ids) != list(range(64)):
        errors.append("ID range broken or contains duplicates")

    for op_id, name, trit, feat in ALL_OPS:
        if trit[CA] != +1:
            errors.append(f"0x{op_id:02X} {name}: CA channel must be +1")
        if int(feat[6]) != TONGUE_ID_CA:
            errors.append(f"0x{op_id:02X} {name}: tongue_id must be {TONGUE_ID_CA}")
        if int(feat[0]) != op_id:
            errors.append(f"0x{op_id:02X} {name}: Z_proxy should match opcode")
        if not (0.0 <= float(feat[4]) <= 4.0):
            errors.append(f"0x{op_id:02X} {name}: chi out of range")
        if any(int(value) not in (-1, 0, 1) for value in trit):
            errors.append(f"0x{op_id:02X} {name}: invalid trit value present")

    return not errors, errors


def get_ca_opcode(op_id: int) -> CAOpcodeEntry:
    try:
        return OP_TABLE[int(op_id)]
    except KeyError as exc:
        raise KeyError(f"Unknown CA opcode: {op_id}") from exc


def _ca_negative_state(entry: CAOpcodeEntry) -> bool:
    chi = float(entry.feat[4])
    return bool(entry.trit[DR] == -1 or entry.trit[UM] == -1 or chi >= 0.8)


def _ca_dual_state(entry: CAOpcodeEntry) -> DualState:
    if entry.trit[DR] == -1 or entry.trit[KO] == -1 or entry.trit[UM] == -1:
        return 1
    return 0


def _ca_resilience(entry: CAOpcodeEntry) -> float:
    period = float(entry.feat[2])
    valence = float(entry.feat[3])
    band = int(entry.feat[5])
    base = 0.28 + (0.08 * period) + (0.03 * min(valence, 3.0))
    if band == 3:
        base += 0.08
    if entry.trit[DR] == -1:
        base -= 0.10
    return float(max(0.05, min(0.98, base)))


def _ca_adaptivity(entry: CAOpcodeEntry) -> float:
    valence = float(entry.feat[3])
    band = int(entry.feat[5])
    base = 0.22 + (0.09 * min(valence, 3.0))
    if entry.trit[RU] == +1:
        base += 0.10
    if entry.trit[DR] != 0:
        base += 0.08
    if band == 1:
        base -= 0.03
    return float(max(0.05, min(0.99, base)))


def _ca_trust_baseline(entry: CAOpcodeEntry, *, resilience: float, adaptivity: float) -> float:
    chi = float(entry.feat[4])
    base = 0.10 + (0.55 * resilience) + (0.20 * adaptivity)
    base -= min(0.20, chi * 0.08)
    if entry.trit[DR] == -1:
        base -= 0.08
    return float(max(0.0, min(1.0, base)))


def ca_opcode_to_atomic_state(op_id: int) -> AtomicTokenState:
    entry = get_ca_opcode(op_id)
    feat = entry.feat
    element = Element(
        symbol=entry.name[:2].upper(),
        Z=int(feat[0]),
        group=int(feat[1]),
        period=int(feat[2]),
        valence=int(feat[3]),
        electronegativity=float(feat[4]),
        witness_stable=False,
    )
    tau = TritVector(
        KO=int(entry.trit[KO]),
        AV=int(entry.trit[AV]),
        RU=int(entry.trit[RU]),
        CA=int(entry.trit[CA]),
        UM=int(entry.trit[UM]),
        DR=int(entry.trit[DR]),
    )
    resilience = _ca_resilience(entry)
    adaptivity = _ca_adaptivity(entry)
    return AtomicTokenState(
        token=entry.name,
        language="c",
        code_lane="c",
        context_class="ca_opcode",
        semantic_class="ACTION",
        element=element,
        tau=tau,
        negative_state=_ca_negative_state(entry),
        dual_state=_ca_dual_state(entry),
        band_flag=int(feat[5]),
        resilience=resilience,
        adaptivity=adaptivity,
        trust_baseline=_ca_trust_baseline(entry, resilience=resilience, adaptivity=adaptivity),
    )


def ca_opcodes_to_atomic_states(op_ids: Sequence[int]) -> list[AtomicTokenState]:
    return [ca_opcode_to_atomic_state(op_id) for op_id in op_ids]


def fuse_ca_opcodes(
    op_ids: Sequence[int],
    *,
    params: FusionParams | None = None,
) -> FusionResult:
    states = ca_opcodes_to_atomic_states(op_ids)
    return fuse_atomic_states(states, params=params)


def collision_report() -> dict[str, list[int]]:
    channels = {"KO": KO, "AV": AV, "RU": RU, "UM": UM, "DR": DR}
    report: dict[str, list[int]] = {}
    for name, idx in channels.items():
        writers = [entry.op_id for entry in OP_TABLE.values() if int(entry.trit[idx]) == +1]
        if len(writers) > 1:
            report[name] = writers
    return report


def print_ca_table() -> str:
    lines = [
        f"{'ID':>4}  {'Name':<12}  {'KO':>3} {'AV':>3} {'RU':>3} {'CA':>3} {'UM':>3} {'DR':>3}  {'chi':>5}  {'band':>4}  {'val':>3}  {'per':>3}"
    ]
    lines.append("-" * 72)
    for op_id, name, trit, feat in ALL_OPS:
        band_name = BAND_NAMES[int(feat[5])]
        lines.append(
            f"0x{op_id:02X}  {name:<12}  {trit[KO]:+2d} {trit[AV]:+2d} {trit[RU]:+2d} {trit[CA]:+2d} {trit[UM]:+2d} {trit[DR]:+2d}  {feat[4]:5.1f}  {band_name:>4}  {int(feat[3]):3d}  {int(feat[2]):3d}"
        )
    return "\n".join(lines)


__all__ = [
    "CAOpcodeEntry",
    "ALL_OPS",
    "OP_TABLE",
    "TRIT_MATRIX",
    "FEAT_MATRIX",
    "NAMES",
    "TONGUE_ID_CA",
    "validate_ca_table",
    "get_ca_opcode",
    "ca_opcode_to_atomic_state",
    "ca_opcodes_to_atomic_states",
    "fuse_ca_opcodes",
    "collision_report",
    "print_ca_table",
]
