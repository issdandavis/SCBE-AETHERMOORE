"""Cassisivadan (CA) — 64-Op Trit Table.

Sacred Tongue of Math & Logic | Target language: C
Patent: US Provisional #63/961,403

Stage 3 of Prism->Rainbow->Beam: per-tongue trit lookup.

Cassisivadan is the math/logic tongue, so its 64-op vocabulary is
domain-specific (pure math + bit logic + comparison + aggregation),
NOT the general fnir.Op programming vocabulary used by other tongues.
This is the periodic-table analogy: every tongue has 64 slots, but
each tongue fills them with the ops native to its dialect.

BANDS (16 ops each):
    0x00-0x0F  Arithmetic   (band=2, group=1)  add, sub, mul, div, ...
    0x10-0x1F  Logic        (band=2, group=2)  and, or, not, xor, ...
    0x20-0x2F  Comparison   (band=1, group=3)  eq, lt, gt, cmp, ...
    0x30-0x3F  Aggregation  (band=3, group=4)  sum, reduce, fold, ...

Each row carries:
  - 6-trit polarity vector across (KO, AV, RU, CA, UM, DR) channels
    where CA is always +1 (home tongue)
  - 8-feature atomic vector [Z, group, period, valence, chi, band,
    tongue_id, reserved]
  - negative_state / dual_state markers from the atomic_tokenization
    pipeline so this table feeds straight into the training bundle.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

TONGUE_ID_CA = 3  # KO=0 AV=1 RU=2 CA=3 UM=4 DR=5
PATENT_REF = "US Provisional #63/961,403"


# --- Op vocabulary (64 entries, math-domain) -----------------------------
CA_OPS: List[str] = [
    # Arithmetic (0x00-0x0F)
    "add",
    "sub",
    "mul",
    "div",
    "mod",
    "pow",
    "sqrt",
    "log",
    "exp",
    "abs",
    "neg",
    "inc",
    "dec",
    "floor",
    "ceil",
    "round",
    # Logic (0x10-0x1F)
    "and",
    "or",
    "not",
    "xor",
    "nand",
    "nor",
    "shl",
    "shr",
    "rotl",
    "rotr",
    "popcount",
    "clz",
    "ctz",
    "bitmask",
    "bitset",
    "bitclear",
    # Comparison (0x20-0x2F)
    "eq",
    "neq",
    "lt",
    "lte",
    "gt",
    "gte",
    "cmp",
    "min",
    "max",
    "clamp",
    "within",
    "isnan",
    "isinf",
    "isfinite",
    "sign",
    "classify",
    # Aggregation (0x30-0x3F)
    "sum",
    "product",
    "mean",
    "variance",
    "stdev",
    "reduce",
    "fold",
    "scan",
    "filter",
    "map",
    "zip",
    "unzip",
    "sort",
    "unique",
    "count",
    "accum",
]
assert len(CA_OPS) == 64, f"CA_OPS must be exactly 64, got {len(CA_OPS)}"

OP_ID: Dict[str, int] = {name: i for i, name in enumerate(CA_OPS)}


# --- Band metadata -------------------------------------------------------
BANDS = [
    ("ARITHMETIC", 0x00, 0x0F, 2, 1),
    ("LOGIC", 0x10, 0x1F, 2, 2),
    ("COMPARISON", 0x20, 0x2F, 1, 3),
    ("AGGREGATION", 0x30, 0x3F, 3, 4),
]


def _band_for(op_id: int) -> Tuple[str, int, int]:
    for name, lo, hi, band, group in BANDS:
        if lo <= op_id <= hi:
            return name, band, group
    raise ValueError(f"op_id {op_id} out of range")


# --- Trit polarity matrix (64, 6) ----------------------------------------
# Channels: (KO, AV, RU, CA, UM, DR). CA channel is always +1 (home).
# Polarity: +1 active/write, 0 witness/read, -1 blocking/negate.
TRIT_MATRIX = np.zeros((64, 6), dtype=np.int8)


def _set_trit(op: str, ko: int, av: int, ru: int, um: int, dr: int) -> None:
    i = OP_ID[op]
    TRIT_MATRIX[i] = (ko, av, ru, +1, um, dr)


for op in (
    "add",
    "sub",
    "mul",
    "div",
    "mod",
    "pow",
    "sqrt",
    "log",
    "exp",
    "abs",
    "neg",
    "inc",
    "dec",
    "floor",
    "ceil",
    "round",
):
    _set_trit(op, +1, +1, +1, +1, +1)

for op in ("and", "or", "xor", "shl", "shr", "rotl", "rotr", "popcount", "clz", "ctz", "bitmask", "bitset"):
    _set_trit(op, +1, +1, +1, +1, +1)
for op in ("not", "nand", "nor", "bitclear"):
    _set_trit(op, +1, +1, +1, +1, -1)

for op in ("eq", "neq", "lt", "lte", "gt", "gte", "cmp"):
    _set_trit(op, 0, +1, +1, +1, +1)
for op in ("min", "max", "clamp", "within"):
    _set_trit(op, +1, +1, +1, +1, +1)
for op in ("isnan", "isinf"):
    _set_trit(op, 0, +1, +1, 0, -1)
_set_trit("isfinite", 0, +1, +1, +1, +1)
_set_trit("sign", 0, +1, +1, +1, +1)
_set_trit("classify", 0, +1, +1, 0, +1)

for op in (
    "sum",
    "product",
    "mean",
    "variance",
    "stdev",
    "reduce",
    "fold",
    "scan",
    "map",
    "zip",
    "unzip",
    "filter",
    "count",
    "accum",
):
    _set_trit(op, +1, +1, +1, +1, +1)
for op in ("sort", "unique"):
    _set_trit(op, +1, +1, +1, +1, -1)


# --- Atomic feature matrix (64, 8) ---------------------------------------
# [Z_proxy, group, period, valence, chi, band, tongue_id, reserved]
FEAT_MATRIX = np.zeros((64, 8), dtype=np.float32)
for i, op in enumerate(CA_OPS):
    _, band, group = _band_for(i)
    period = (i // 16) + 1
    valence = (i % 8) + 1
    chi = 0.10 + 0.02 * (i % 16)
    FEAT_MATRIX[i] = (
        float(i + 1),
        float(group),
        float(period),
        float(valence),
        float(chi),
        float(band),
        float(TONGUE_ID_CA),
        0.0,
    )


# --- Negative-state / dual-state reducer metadata ------------------------
# Wired to python/scbe/atomic_tokenization.py so the training bundle
# carries trust + negative_state + dual_state + drift per op.
@dataclass
class ReducerMeta:
    op: str
    op_id: int
    negative_state: bool
    dual_state: bool
    drift_norm: float

    def to_dict(self) -> dict:
        return {
            "op": self.op,
            "op_id": self.op_id,
            "negative_state": self.negative_state,
            "dual_state": self.dual_state,
            "drift_norm": self.drift_norm,
            "tongue": "CA",
            "patent": PATENT_REF,
        }


def _reducer_for(op: str) -> ReducerMeta:
    i = OP_ID[op]
    is_neg = op in {
        "not",
        "nand",
        "nor",
        "bitclear",
        "neg",
        "sub",
        "isnan",
        "isinf",
    }
    is_dual = op in {
        "cmp",
        "classify",
        "clamp",
        "within",
        "sign",
        "scan",
        "fold",
        "reduce",
        "unzip",
    }
    drift = float(np.linalg.norm(TRIT_MATRIX[i].astype(np.float32))) / 6.0
    return ReducerMeta(op=op, op_id=i, negative_state=is_neg, dual_state=is_dual, drift_norm=drift)


REDUCER_META: Dict[str, ReducerMeta] = {op: _reducer_for(op) for op in CA_OPS}


# --- Lookup helpers ------------------------------------------------------
def lookup(op: str) -> Tuple[np.ndarray, np.ndarray, ReducerMeta]:
    i = OP_ID[op]
    return TRIT_MATRIX[i], FEAT_MATRIX[i], REDUCER_META[op]


def lookup_id(op_id: int) -> Tuple[str, np.ndarray, np.ndarray, ReducerMeta]:
    op = CA_OPS[op_id]
    t, f, r = lookup(op)
    return op, t, f, r


def trit_stream(ops: List[str]) -> np.ndarray:
    return np.stack([TRIT_MATRIX[OP_ID[o]] for o in ops])


def atomic_stream(ops: List[str]) -> np.ndarray:
    return np.stack([FEAT_MATRIX[OP_ID[o]] for o in ops])


def collision_report(ops_a: List[str], ops_b: List[str], channel: int = 0) -> Dict[str, int]:
    """ww/wr/wn breakdown on a chosen channel between two op streams."""
    a = trit_stream(ops_a)[:, channel]
    b = trit_stream(ops_b)[:, channel]
    n = min(len(a), len(b))
    ww = wr = wn = 0
    for i in range(n):
        pa, pb = int(a[i]), int(b[i])
        if pa == 1 and pb == 1:
            ww += 1
        elif (pa == 1 and pb == 0) or (pa == 0 and pb == 1):
            wr += 1
        elif (pa == 1 and pb == -1) or (pa == -1 and pb == 1):
            wn += 1
    return {"ww": ww, "wr": wr, "wn": wn, "steps": n}


# --- Axiom self-validation -----------------------------------------------
def validate() -> Dict[str, bool]:
    results: Dict[str, bool] = {}

    # A1 Unitarity: every row's CA channel = +1 (home tongue norm)
    results["A1_unitarity"] = bool(np.all(TRIT_MATRIX[:, TONGUE_ID_CA] == 1))

    # A2 Locality: feature rows match their band's group/band window
    a2 = True
    for i in range(64):
        _, band, group = _band_for(i)
        if FEAT_MATRIX[i, 1] != group or FEAT_MATRIX[i, 5] != band:
            a2 = False
            break
    results["A2_locality"] = a2

    # A3 Causality: monotone band layout, no jumps > 1
    a3 = True
    for i in range(63):
        if FEAT_MATRIX[i, 5] > FEAT_MATRIX[i + 1, 5] + 1:
            a3 = False
            break
    results["A3_causality"] = a3

    # A4 Symmetry: every op acts on at least one channel
    nonzero = np.any(TRIT_MATRIX != 0, axis=1)
    results["A4_symmetry"] = bool(np.all(nonzero))

    # A5 Composition: shapes + counts consistent end-to-end
    results["A5_composition"] = (
        len(CA_OPS) == 64
        and len(REDUCER_META) == 64
        and len(BANDS) == 4
        and TRIT_MATRIX.shape == (64, 6)
        and FEAT_MATRIX.shape == (64, 8)
    )

    results["all_pass"] = all(v for k, v in results.items() if k != "all_pass")
    return results


def print_table() -> None:
    print(f"Cassisivadan (CA) trit table   patent: {PATENT_REF}")
    print(f"{'id':<5}{'op':<12}{'band':<14}" f"{'trit (KO AV RU CA UM DR)':<28}" f"{'neg':<5}{'dual':<5}{'drift':<8}")
    for i, op in enumerate(CA_OPS):
        band_name, _, _ = _band_for(i)
        t = TRIT_MATRIX[i]
        r = REDUCER_META[op]
        trit_str = " ".join(f"{int(x):+d}" for x in t)
        print(
            f"0x{i:02X} {op:<12}{band_name:<14}{trit_str:<28}"
            f"{'Y' if r.negative_state else '.':<5}"
            f"{'Y' if r.dual_state else '.':<5}"
            f"{r.drift_norm:<8.3f}"
        )


if __name__ == "__main__":
    print_table()
    print("\n=== AXIOM CHECK ===")
    for k, v in validate().items():
        print(f"  {k:<18} {'PASS' if v else 'FAIL'}")

    print("\n=== COLLISION (add/mul/sum vs sub/div/mean, KO channel) ===")
    a = ["add", "mul", "add", "sum", "fold"]
    b = ["sub", "div", "sub", "mean", "scan"]
    print(collision_report(a, b, channel=0))
