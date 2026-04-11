"""Draumric (DR) — 64-Op Trit Table.

Sacred Tongue of Lock & Purity | Target language: Haskell
Patent: US Provisional #63/961,403

Draumric is the lock/causality tongue — purity, monadic effects,
explicit IO boundary, lazy evaluation. Its 64 ops fill Haskell's
native pure/monad/effect/lazy slots.

BANDS (16 ops each):
    0x00-0x0F  Pure     (band=1, group=1)  let, letrec, lambda, ...
    0x10-0x1F  Monad    (band=2, group=2)  bind, return, do, ...
    0x20-0x2F  Effect   (band=2, group=3)  io, ref, st, exception, ...
    0x30-0x3F  Lazy     (band=3, group=4)  thunk, force, seq, ...
"""

from __future__ import annotations
from typing import Tuple

from ._trit_common import TritTable, build_trit_table

TONGUE = "DR"
TONGUE_ID = 5

OPS = [
    # Pure (0x00-0x0F)
    "let_d", "letrec", "lambda_d", "apply", "compose", "curry", "uncurry", "flip_",
    "id_d", "const_d", "fix_", "church", "pair_d", "fst_", "snd_", "either_",
    # Monad (0x10-0x1F)
    "bind_d", "return_d", "do_", "pure_", "ap_", "fmap_", "join_", "lift",
    "mplus", "mzero", "guard_", "when_", "unless_", "sequence_d", "mapm", "foldm",
    # Effect (0x20-0x2F)
    "io_", "ref_d", "st_", "mvar", "tvar", "exception_d", "throw_", "handle_",
    "bracket", "finally", "mask_", "async_d", "par_", "unsafe_io", "perform", "forever",
    # Lazy (0x30-0x3F)
    "thunk", "force_", "seq_", "deepseq", "strict", "bang", "whnf", "nf_",
    "memo", "stream_d", "fold", "unfold", "take_d", "drop_d", "iter_d", "cycle_",
]

BANDS = [
    ("PURE",   0x00, 0x0F, 1, 1),
    ("MONAD",  0x10, 0x1F, 2, 2),
    ("EFFECT", 0x20, 0x2F, 2, 3),
    ("LAZY",   0x30, 0x3F, 3, 4),
]

NEG_OPS = {
    "flip_",
    "mzero", "unless_",
    "exception_d", "throw_", "unsafe_io",
    "drop_",
}

DUAL_OPS = {
    "either_", "fix_",
    "bind_d", "do_", "ap_", "mplus", "guard_",
    "handle_", "bracket", "mask_", "async_d",
    "thunk", "strict", "memo", "stream_d", "unfold",
}


def _polarity(op: str) -> Tuple[int, int, int, int, int, int]:
    """(KO, AV, RU, CA, UM, DR) polarity — DR home forced +1 by factory."""
    # Pure ops: witness-mostly across all channels (referential transparency)
    if op in {"let_d", "letrec", "lambda_d", "apply", "compose",
              "curry", "uncurry", "id_d", "const_d", "church",
              "pair_d", "fst_", "snd_"}:
        return (+1, +1, 0, 0, 0, +1)
    if op in {"flip_"}:
        return (+1, +1, 0, 0, +1, -1)
    if op in {"fix_", "either_"}:
        return (+1, +1, 0, 0, +1, +1)

    # Monad ops: active on KO (intent/sequencing) + DR
    if op in {"bind_d", "return_d", "do_", "pure_", "ap_",
              "fmap_", "join_", "lift", "sequence_d", "mapm", "foldm"}:
        return (+1, +1, +1, 0, 0, +1)
    if op in {"mplus", "guard_", "when_"}:
        return (+1, +1, 0, 0, +1, +1)
    if op in {"mzero", "unless_"}:
        return (+1, +1, 0, 0, +1, -1)

    # Effect ops: active on CA (execution) — the IO/ST boundary
    if op in {"io_", "ref_d", "st_", "mvar", "tvar",
              "bracket", "finally", "mask_", "async_d",
              "par_", "perform", "forever"}:
        return (+1, +1, +1, +1, +1, +1)
    if op in {"exception_d", "throw_"}:
        return (+1, +1, -1, +1, +1, -1)
    if op in {"handle_"}:
        return (+1, +1, +1, +1, +1, +1)
    if op in {"unsafe_io"}:
        return (+1, 0, -1, +1, -1, -1)   # escape hatch

    # Lazy ops: active on UM (stability/suppression) + DR
    if op in {"thunk", "force_", "seq_", "deepseq", "strict",
              "bang", "whnf", "nf_", "memo", "stream_d",
              "fold", "unfold", "take_d", "iter_d", "cycle_"}:
        return (+1, +1, 0, +1, +1, +1)
    if op in {"drop_d"}:
        return (+1, +1, 0, +1, +1, -1)

    return (0, +1, 0, 0, 0, +1)


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
