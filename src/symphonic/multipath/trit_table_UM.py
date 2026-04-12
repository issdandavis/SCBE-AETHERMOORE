"""Umbroth (UM) — 64-Op Trit Table.

Sacred Tongue of Suppression & Dispatch | Target language: Julia
Patent: US Provisional #63/961,403

Umbroth is the suppression/stabilization tongue — multiple dispatch,
numeric precision, array broadcasting, scientific primitives. Its
64 ops fill Julia's native dispatch/numeric/array/science slots.

BANDS (16 ops each):
    0x00-0x0F  Dispatch (band=1, group=1)  func, multi, where, ...
    0x10-0x1F  Numeric  (band=2, group=2)  int, float, complex, ...
    0x20-0x2F  Array    (band=2, group=3)  matrix, broadcast, dot, ...
    0x30-0x3F  Science  (band=3, group=4)  diff, integ, solve, fft, ...
"""

from __future__ import annotations
from typing import Tuple

from ._trit_common import TritTable, build_trit_table

TONGUE = "UM"
TONGUE_ID = 4

OPS = [
    # Dispatch (0x00-0x0F)
    "func",
    "multi",
    "where_u",
    "specialize",
    "invoke",
    "method",
    "signature",
    "abstract_t",
    "concrete",
    "subtype",
    "supertype",
    "union_t",
    "typevar",
    "promote",
    "convert",
    "cast",
    # Numeric (0x10-0x1F)
    "int_",
    "float_",
    "complex_",
    "rational",
    "bignum",
    "irrational",
    "bool_u",
    "char_u",
    "prec",
    "round_",
    "floor_",
    "ceil_",
    "trunc_",
    "sign_",
    "abs_",
    "hypot",
    # Array (0x20-0x2F)
    "matrix",
    "vector",
    "tensor",
    "broadcast",
    "dot_",
    "cross_",
    "outer",
    "kron",
    "reshape",
    "transpose",
    "reduce_",
    "scan_",
    "axis",
    "stack_",
    "split_u",
    "view_",
    # Science (0x30-0x3F)
    "diff_",
    "integ",
    "solve_",
    "fft_",
    "eig",
    "svd",
    "qr_",
    "lu_",
    "norm_",
    "det_",
    "inv_",
    "rand_",
    "stat",
    "corr",
    "fit_",
    "optimize",
]

BANDS = [
    ("DISPATCH", 0x00, 0x0F, 1, 1),
    ("NUMERIC", 0x10, 0x1F, 2, 2),
    ("ARRAY", 0x20, 0x2F, 2, 3),
    ("SCIENCE", 0x30, 0x3F, 3, 4),
]

NEG_OPS = {
    "cast",
    "trunc_",
    "split_u",
    "diff_",
    "inv_",
}

DUAL_OPS = {
    "multi",
    "specialize",
    "promote",
    "convert",
    "abstract_t",
    "subtype",
    "supertype",
    "union_t",
    "typevar",
    "broadcast",
    "reduce_",
    "scan_",
    "solve_",
    "eig",
    "svd",
    "optimize",
}


def _polarity(op: str) -> Tuple[int, int, int, int, int, int]:
    """(KO, AV, RU, CA, UM, DR) polarity — UM home forced +1 by factory."""
    # Dispatch ops: active on AV (type) + DR (lock)
    if op in {"func", "multi", "where_u", "specialize", "invoke", "method", "signature", "promote", "convert"}:
        return (+1, +1, 0, 0, +1, +1)
    if op in {"abstract_t", "concrete", "subtype", "supertype", "union_t", "typevar"}:
        return (0, +1, 0, 0, +1, +1)
    if op in {"cast"}:
        return (+1, +1, -1, +1, +1, -1)

    # Numeric ops: active on CA (execution)
    if op in {
        "int_",
        "float_",
        "complex_",
        "rational",
        "bignum",
        "irrational",
        "bool_u",
        "char_u",
        "prec",
        "round_",
        "floor_",
        "ceil_",
        "sign_",
        "abs_",
        "hypot",
    }:
        return (0, +1, 0, +1, +1, +1)
    if op in {"trunc_"}:
        return (0, +1, 0, +1, +1, -1)

    # Array ops: active on CA + cross-coupling via broadcast
    if op in {
        "matrix",
        "vector",
        "tensor",
        "dot_",
        "cross_",
        "outer",
        "kron",
        "reshape",
        "transpose",
        "axis",
        "stack_",
        "view_",
    }:
        return (+1, +1, +1, +1, +1, +1)
    if op in {"broadcast", "reduce_", "scan_"}:
        return (+1, +1, 0, +1, +1, +1)
    if op in {"split_u"}:
        return (+1, +1, 0, +1, +1, -1)

    # Science ops: active across all channels (heavy compute)
    if op in {
        "integ",
        "solve_",
        "fft_",
        "eig",
        "svd",
        "qr_",
        "lu_",
        "norm_",
        "det_",
        "rand_",
        "stat",
        "corr",
        "fit_",
        "optimize",
    }:
        return (+1, +1, +1, +1, +1, +1)
    if op in {"diff_", "inv_"}:
        return (+1, +1, 0, +1, +1, -1)

    return (0, +1, 0, +1, +1, 0)


TABLE: TritTable = build_trit_table(
    tongue=TONGUE,
    tongue_id=TONGUE_ID,
    ops=OPS,
    bands=BANDS,
    polarity=_polarity,
    neg_ops=NEG_OPS,
    dual_ops=DUAL_OPS,
)


if __name__ == "__main__":
    TABLE.print_table()
    print("\n=== AXIOM CHECK ===")
    for k, v in TABLE.validate().items():
        print(f"  {k:<18} {'PASS' if v else 'FAIL'}")
