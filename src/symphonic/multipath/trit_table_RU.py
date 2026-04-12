"""Runethic (RU) — 64-Op Trit Table.

Sacred Tongue of Memory & Ownership | Target language: Rust
Patent: US Provisional #63/961,403

Runethic is the memory/ownership tongue — affine types, borrow
checker, traits, explicit error handling. Its 64 ops fill Rust's
native ownership/borrow/trait/error slots.

BANDS (16 ops each):
    0x00-0x0F  Own      (band=1, group=1)  own, move, drop, box, ...
    0x10-0x1F  Borrow   (band=2, group=2)  ref, mut, lifetime, ...
    0x20-0x2F  Trait    (band=2, group=3)  trait, impl, derive, ...
    0x30-0x3F  Error    (band=3, group=4)  result, ok, err, panic, ...
"""

from __future__ import annotations
from typing import Tuple

from ._trit_common import TritTable, build_trit_table

TONGUE = "RU"
TONGUE_ID = 2

OPS = [
    # Own (0x00-0x0F)
    "own", "move_", "drop_", "box_", "rc_", "arc_", "cell_", "refcell",
    "pin_", "leak", "forget", "take_", "replace", "swap_", "clone_", "copy_",
    # Borrow (0x10-0x1F)
    "ref_", "ref_mut", "deref_", "lifetime", "static_ref", "slice_", "str_ref", "borrow",
    "borrow_mut", "reborrow", "split", "share", "alias_ref", "unsafe_", "raw_ptr", "null_ptr",
    # Trait (0x20-0x2F)
    "trait_", "impl_", "derive", "dyn_", "sized", "send", "sync", "bound",
    "where_", "assoc", "default_", "blanket", "supertrait", "object_safe", "generic_t", "phantom",
    # Error (0x30-0x3F)
    "result", "ok_", "err_", "option", "some_", "none_", "unwrap", "expect",
    "map_err", "and_then", "or_else", "try_op", "panic_", "abort", "catch_unwind", "propagate",
]

BANDS = [
    ("OWN",    0x00, 0x0F, 1, 1),
    ("BORROW", 0x10, 0x1F, 2, 2),
    ("TRAIT",  0x20, 0x2F, 2, 3),
    ("ERROR",  0x30, 0x3F, 3, 4),
]

NEG_OPS = {
    "drop_", "leak", "forget", "swap_",
    "ref_mut", "unsafe_", "null_ptr",
    "err_", "none_", "panic_", "abort", "catch_unwind",
}

DUAL_OPS = {
    "cell_", "refcell", "pin_",
    "borrow", "borrow_mut", "reborrow", "split", "share",
    "dyn_", "blanket", "object_safe", "phantom",
    "result", "option", "try_op", "propagate",
}


def _polarity(op: str) -> Tuple[int, int, int, int, int, int]:
    """(KO, AV, RU, CA, UM, DR) polarity — RU home forced +1 by factory."""
    # Own ops: active on DR (lock), write on CA (memory)
    if op in {"own", "move_", "box_", "rc_", "arc_",
              "pin_", "take_", "replace", "clone_", "copy_"}:
        return (+1, 0, +1, +1, +1, +1)
    if op in {"drop_", "leak", "forget", "swap_"}:
        return (+1, 0, +1, -1, +1, -1)
    if op in {"cell_", "refcell"}:
        return (+1, +1, +1, +1, 0, +1)

    # Borrow ops: active across CA (pointer) + UM (lifetime constraint)
    if op in {"ref_", "deref_", "lifetime", "static_ref", "slice_",
              "str_ref", "borrow", "reborrow", "split", "share", "alias_ref"}:
        return (0, +1, +1, +1, +1, +1)
    if op in {"ref_mut", "borrow_mut"}:
        return (+1, 0, +1, +1, +1, -1)   # mutation breaks shared lock
    if op in {"unsafe_", "raw_ptr", "null_ptr"}:
        return (+1, 0, +1, +1, -1, -1)   # escape hatch

    # Trait ops: witness + structural; feed AV type lattice
    if op in {"trait_", "impl_", "derive", "sized", "send", "sync",
              "bound", "where_", "assoc", "default_", "supertrait",
              "generic_t"}:
        return (0, +1, +1, 0, +1, +1)
    if op in {"dyn_", "blanket", "object_safe", "phantom"}:
        return (0, +1, +1, 0, 0, +1)

    # Error ops: active on DR; failure branches invert
    if op in {"result", "ok_", "option", "some_",
              "map_err", "and_then", "or_else", "try_op", "propagate"}:
        return (+1, +1, +1, 0, +1, +1)
    if op in {"err_", "none_"}:
        return (+1, +1, +1, 0, +1, -1)
    if op in {"unwrap", "expect"}:
        return (+1, 0, +1, +1, -1, -1)   # ignores failure path
    if op in {"panic_", "abort", "catch_unwind"}:
        return (+1, +1, +1, -1, +1, -1)

    return (0, 0, +1, 0, 0, 0)


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
