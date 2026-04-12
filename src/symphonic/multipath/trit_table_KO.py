"""Kor'aelin (KO) — 64-Op Trit Table.

Sacred Tongue of Intent & Control | Target language: Python
Patent: US Provisional #63/961,403

Kor'aelin is the intent/binding tongue, so its 64-op vocabulary is
domain-specific: bind/closure/control-flow/iter/introspect. This is
the periodic-table analogy — KO fills its 64 slots with Python-native
binding and control ops, NOT CA's math primitives.

BANDS (16 ops each):
    0x00-0x0F  Bind         (band=1, group=1)  bind, unpack, lambda, ...
    0x10-0x1F  Control      (band=2, group=2)  if, while, for, try, ...
    0x20-0x2F  Iter         (band=2, group=3)  iter, next, map, zip, ...
    0x30-0x3F  Introspect   (band=3, group=4)  type, len, repr, hash, ...
"""

from __future__ import annotations
from typing import Tuple

from ._trit_common import TritTable, build_trit_table

TONGUE = "KO"
TONGUE_ID = 0

OPS = [
    # Bind (0x00-0x0F)
    "bind",
    "unpack",
    "destructure",
    "lambda",
    "closure",
    "scope",
    "capture",
    "alias",
    "rebind",
    "shadow",
    "freeze",
    "thaw",
    "ref",
    "deref",
    "swap",
    "ident",
    # Control (0x10-0x1F)
    "if_",
    "elif_",
    "else_",
    "while_",
    "for_",
    "break_",
    "continue_",
    "pass_",
    "return_",
    "yield_",
    "raise_",
    "try_",
    "except_",
    "finally_",
    "with_",
    "match_",
    # Iter (0x20-0x2F)
    "iter",
    "next",
    "range",
    "enumerate",
    "zip",
    "map_",
    "filter_",
    "take",
    "drop",
    "chain",
    "flatten",
    "group",
    "partition",
    "slice",
    "step",
    "reverse",
    # Introspect (0x30-0x3F)
    "type_",
    "isinstance_",
    "hasattr_",
    "getattr_",
    "setattr_",
    "delattr_",
    "dir_",
    "vars_",
    "callable_",
    "len_",
    "repr_",
    "str_",
    "hash_",
    "id_",
    "eq_",
    "copy_",
]

BANDS = [
    ("BIND", 0x00, 0x0F, 1, 1),
    ("CONTROL", 0x10, 0x1F, 2, 2),
    ("ITER", 0x20, 0x2F, 2, 3),
    ("INTROSPECT", 0x30, 0x3F, 3, 4),
]

# Ops that negate / invert a downstream channel
NEG_OPS = {
    "thaw",
    "swap",
    "break_",
    "continue_",
    "raise_",
    "except_",
    "filter_",
    "drop",
    "partition",
    "reverse",
    "delattr_",
    "eq_",  # eq can yield False = negative signal
}

# Ops whose semantics carry dual (branching) state
DUAL_OPS = {
    "if_",
    "elif_",
    "else_",
    "try_",
    "match_",
    "partition",
    "group",
    "isinstance_",
    "hasattr_",
    "callable_",
}


def _polarity(op: str) -> Tuple[int, int, int, int, int, int]:
    """(KO, AV, RU, CA, UM, DR) polarity for each op.

    KO channel is forced to +1 by build_trit_table (A1 home norm).
    Other channels: +1 active, 0 witness/read, -1 blocking.
    """
    # Bind ops: active on KO (self), witness others, DR locks bindings
    if op in {
        "bind",
        "unpack",
        "destructure",
        "lambda",
        "closure",
        "scope",
        "capture",
        "alias",
        "rebind",
        "shadow",
        "freeze",
        "ref",
        "ident",
    }:
        return (+1, +1, +1, 0, +1, +1)
    if op in {"thaw", "deref", "swap"}:
        return (+1, +1, -1, 0, +1, -1)  # inverts RU ownership + DR lock

    # Control ops: active on KO + DR (causality)
    if op in {"if_", "elif_", "else_", "while_", "for_", "return_", "yield_", "with_", "match_"}:
        return (+1, +1, 0, 0, +1, +1)
    if op in {"break_", "continue_", "pass_"}:
        return (+1, 0, 0, 0, +1, -1)
    if op in {"raise_", "try_", "except_", "finally_"}:
        return (+1, +1, -1, 0, +1, -1)  # exceptions invert RU+DR

    # Iter ops: active across collection tongues (AV+CA arrays)
    if op in {
        "iter",
        "next",
        "range",
        "enumerate",
        "zip",
        "map_",
        "take",
        "chain",
        "flatten",
        "group",
        "slice",
        "step",
    }:
        return (+1, +1, 0, +1, +1, +1)
    if op in {"filter_", "drop", "partition", "reverse"}:
        return (+1, +1, 0, +1, +1, -1)

    # Introspect ops: read-mostly, witness everything
    if op in {
        "type_",
        "isinstance_",
        "hasattr_",
        "getattr_",
        "dir_",
        "vars_",
        "callable_",
        "len_",
        "repr_",
        "str_",
        "hash_",
        "id_",
        "copy_",
    }:
        return (+1, +1, 0, 0, 0, 0)
    if op in {"setattr_", "delattr_", "eq_"}:
        return (+1, +1, -1, 0, 0, -1)

    return (+1, +1, 0, 0, +1, 0)  # safe default


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
