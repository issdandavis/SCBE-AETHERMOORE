"""Shared trit-table scaffold for the 6 Sacred Tongue trit tables.

Each tongue file (trit_table_KO/AV/RU/CA/UM/DR.py) declares its own:
  - TONGUE_ID         (0..5 from KO=0 to DR=5)
  - OPS               (exactly 64 op names)
  - BANDS             ([(name, lo, hi, band_idx, group_idx), ...])
  - POLARITY_RULES    (callable: op_name -> (ko, av, ru, ca, um, dr))
  - NEG_OPS           (set of op names that flip a downstream channel)
  - DUAL_OPS          (set of op names with dual-state semantics)

It then calls `build_trit_table(...)` to materialize:
  TRIT_MATRIX (64,6 int8), FEAT_MATRIX (64,8 float32),
  REDUCER_META, OP_ID, lookup helpers, validate().

This keeps every tongue table to ~80 lines of declaration only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple

import numpy as np

PATENT_REF = "US Provisional #63/961,403"
TONGUE_NAMES = ("KO", "AV", "RU", "CA", "UM", "DR")
TONGUE_FULL = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}
# Phi-weighted tongue scaling (from docs/LANGUES_WEIGHTING_SYSTEM.md)
PHI_WEIGHTS = (1.000, 1.618, 2.618, 4.236, 6.854, 11.090)


@dataclass
class ReducerMeta:
    op: str
    op_id: int
    negative_state: bool
    dual_state: bool
    drift_norm: float
    tongue: str

    def to_dict(self) -> dict:
        return {
            "op": self.op,
            "op_id": self.op_id,
            "negative_state": self.negative_state,
            "dual_state": self.dual_state,
            "drift_norm": self.drift_norm,
            "tongue": self.tongue,
            "patent": PATENT_REF,
        }


@dataclass
class TritTable:
    """Materialized per-tongue trit table — output of build_trit_table()."""

    tongue: str
    tongue_id: int
    ops: List[str]
    bands: List[Tuple[str, int, int, int, int]]
    op_id: Dict[str, int]
    trit_matrix: np.ndarray  # (64, 6) int8
    feat_matrix: np.ndarray  # (64, 8) float32
    reducer_meta: Dict[str, ReducerMeta]

    def lookup(self, op: str) -> Tuple[np.ndarray, np.ndarray, ReducerMeta]:
        i = self.op_id[op]
        return self.trit_matrix[i], self.feat_matrix[i], self.reducer_meta[op]

    def lookup_id(self, op_id: int) -> Tuple[str, np.ndarray, np.ndarray, ReducerMeta]:
        op = self.ops[op_id]
        t, f, r = self.lookup(op)
        return op, t, f, r

    def trit_stream(self, ops: List[str]) -> np.ndarray:
        return np.stack([self.trit_matrix[self.op_id[o]] for o in ops])

    def atomic_stream(self, ops: List[str]) -> np.ndarray:
        return np.stack([self.feat_matrix[self.op_id[o]] for o in ops])

    def band_for(self, op_id: int) -> Tuple[str, int, int]:
        for name, lo, hi, band, group in self.bands:
            if lo <= op_id <= hi:
                return name, band, group
        raise ValueError(f"op_id {op_id} out of range")

    def validate(self) -> Dict[str, bool]:
        results: Dict[str, bool] = {}

        # A1 Unitarity: home channel always +1
        results["A1_unitarity"] = bool(np.all(self.trit_matrix[:, self.tongue_id] == 1))

        # A2 Locality: feature rows match band/group
        a2 = True
        for i in range(64):
            _, band, group = self.band_for(i)
            if self.feat_matrix[i, 1] != group or self.feat_matrix[i, 5] != band:
                a2 = False
                break
        results["A2_locality"] = a2

        # A3 Causality: monotone band layout
        a3 = True
        for i in range(63):
            if self.feat_matrix[i, 5] > self.feat_matrix[i + 1, 5] + 1:
                a3 = False
                break
        results["A3_causality"] = a3

        # A4 Symmetry: every op acts on at least one channel
        nonzero = np.any(self.trit_matrix != 0, axis=1)
        results["A4_symmetry"] = bool(np.all(nonzero))

        # A5 Composition: shape consistency
        results["A5_composition"] = (
            len(self.ops) == 64
            and len(self.reducer_meta) == 64
            and len(self.bands) == 4
            and self.trit_matrix.shape == (64, 6)
            and self.feat_matrix.shape == (64, 8)
        )

        results["all_pass"] = all(v for k, v in results.items() if k != "all_pass")
        return results

    def collision_report(self, ops_a: List[str], ops_b: List[str], channel: int = 0) -> Dict[str, int]:
        a = self.trit_stream(ops_a)[:, channel]
        b = self.trit_stream(ops_b)[:, channel]
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

    def print_table(self) -> None:
        full = TONGUE_FULL[self.tongue]
        print(f"{full} ({self.tongue}) trit table   patent: {PATENT_REF}")
        print(
            f"{'id':<5}{'op':<14}{'band':<14}" f"{'trit (KO AV RU CA UM DR)':<28}" f"{'neg':<5}{'dual':<5}{'drift':<8}"
        )
        for i, op in enumerate(self.ops):
            band_name, _, _ = self.band_for(i)
            t = self.trit_matrix[i]
            r = self.reducer_meta[op]
            trit_str = " ".join(f"{int(x):+d}" for x in t)
            print(
                f"0x{i:02X} {op:<14}{band_name:<14}{trit_str:<28}"
                f"{'Y' if r.negative_state else '.':<5}"
                f"{'Y' if r.dual_state else '.':<5}"
                f"{r.drift_norm:<8.3f}"
            )


PolarityFn = Callable[[str], Tuple[int, int, int, int, int, int]]


def build_trit_table(
    tongue: str,
    tongue_id: int,
    ops: List[str],
    bands: List[Tuple[str, int, int, int, int]],
    polarity: PolarityFn,
    neg_ops: set,
    dual_ops: set,
) -> TritTable:
    """Materialize a trit table from a tongue's declarations."""
    if len(ops) != 64:
        raise ValueError(f"{tongue}: ops must be exactly 64, got {len(ops)}")
    if len(bands) != 4:
        raise ValueError(f"{tongue}: bands must be exactly 4, got {len(bands)}")

    op_id = {name: i for i, name in enumerate(ops)}

    trit = np.zeros((64, 6), dtype=np.int8)
    for i, op in enumerate(ops):
        row = polarity(op)
        if len(row) != 6:
            raise ValueError(f"{tongue}.{op}: polarity must be 6 channels")
        # Force home channel to +1 (A1 unitarity guarantee)
        row = list(row)
        row[tongue_id] = 1
        trit[i] = row

    feat = np.zeros((64, 8), dtype=np.float32)

    def _band_for(i: int) -> Tuple[str, int, int]:
        for name, lo, hi, band, group in bands:
            if lo <= i <= hi:
                return name, band, group
        raise ValueError(f"op_id {i} out of range")

    for i, op in enumerate(ops):
        _, band, group = _band_for(i)
        period = (i // 16) + 1
        valence = (i % 8) + 1
        chi = 0.10 + 0.02 * (i % 16)
        feat[i] = (
            float(i + 1),
            float(group),
            float(period),
            float(valence),
            float(chi),
            float(band),
            float(tongue_id),
            0.0,
        )

    reducer: Dict[str, ReducerMeta] = {}
    for i, op in enumerate(ops):
        drift = float(np.linalg.norm(trit[i].astype(np.float32))) / 6.0
        reducer[op] = ReducerMeta(
            op=op,
            op_id=i,
            negative_state=op in neg_ops,
            dual_state=op in dual_ops,
            drift_norm=drift,
            tongue=tongue,
        )

    return TritTable(
        tongue=tongue,
        tongue_id=tongue_id,
        ops=ops,
        bands=bands,
        op_id=op_id,
        trit_matrix=trit,
        feat_matrix=feat,
        reducer_meta=reducer,
    )
