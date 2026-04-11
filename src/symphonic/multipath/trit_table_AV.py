"""Avali (AV) — 64-Op Trit Table.

Sacred Tongue of Attention & Type | Target language: TypeScript
Patent: US Provisional #63/961,403

Avali is the attention/type tongue — structural typing, async flow,
event orchestration. Its 64 ops fill TypeScript-native type/struct/
async/event slots.

BANDS (16 ops each):
    0x00-0x0F  Type     (band=1, group=1)  number, string, union, ...
    0x10-0x1F  Struct   (band=2, group=2)  interface, class, extends, ...
    0x20-0x2F  Async    (band=2, group=3)  promise, await, then, ...
    0x30-0x3F  Event    (band=3, group=4)  emit, on, off, dispatch, ...
"""

from __future__ import annotations
from typing import Tuple

from ._trit_common import TritTable, build_trit_table

TONGUE = "AV"
TONGUE_ID = 1

OPS = [
    # Type (0x00-0x0F)
    "number", "string", "boolean", "null_", "undef", "any_", "unknown_", "never_",
    "union", "intersect", "tuple", "array", "record", "literal", "enum_", "generic",
    # Struct (0x10-0x1F)
    "interface_", "class_", "extends_", "implements_", "abstract_", "static_", "public_", "private_",
    "protected_", "readonly_", "constructor_", "super_", "this_", "new_", "instanceof_", "typeof_",
    # Async (0x20-0x2F)
    "promise", "await_", "then_", "catch_", "resolve", "reject", "async_", "sync_",
    "defer", "race", "all_", "any_of", "settle", "yield_async", "cancel", "timeout",
    # Event (0x30-0x3F)
    "emit", "on_", "off_", "once_", "dispatch", "listen", "handler", "observer",
    "subject", "stream", "subscribe", "unsubscribe", "publish", "signal", "slot", "topic",
]

BANDS = [
    ("TYPE",   0x00, 0x0F, 1, 1),
    ("STRUCT", 0x10, 0x1F, 2, 2),
    ("ASYNC",  0x20, 0x2F, 2, 3),
    ("EVENT",  0x30, 0x3F, 3, 4),
]

NEG_OPS = {
    "null_", "undef", "never_",
    "private_", "protected_",
    "reject", "cancel", "timeout",
    "off_", "unsubscribe",
}

DUAL_OPS = {
    "union", "intersect", "literal", "generic",
    "extends_", "implements_", "instanceof_", "typeof_",
    "race", "any_of", "settle",
    "subject", "stream",
}


def _polarity(op: str) -> Tuple[int, int, int, int, int, int]:
    """(KO, AV, RU, CA, UM, DR) polarity — AV home forced +1 by factory."""
    # Type ops: witness-mostly; describe shape of data without owning it
    if op in {"number", "string", "boolean", "any_", "unknown_",
              "union", "intersect", "tuple", "array", "record",
              "literal", "enum_", "generic"}:
        return (0, +1, +1, 0, 0, +1)
    if op in {"null_", "undef", "never_"}:
        return (0, +1, -1, 0, +1, -1)   # absence inverts RU+DR

    # Struct ops: active on RU (ownership) + DR (lock)
    if op in {"interface_", "class_", "extends_", "implements_",
              "abstract_", "constructor_", "super_", "this_", "new_"}:
        return (+1, +1, +1, 0, 0, +1)
    if op in {"static_", "readonly_"}:
        return (0, +1, +1, 0, +1, +1)   # UM lock via immutability
    if op in {"public_"}:
        return (0, +1, +1, 0, 0, 0)
    if op in {"private_", "protected_"}:
        return (0, +1, +1, 0, +1, -1)   # visibility block
    if op in {"instanceof_", "typeof_"}:
        return (0, +1, 0, 0, 0, 0)       # pure read

    # Async ops: active on DR (causality/time)
    if op in {"promise", "await_", "then_", "async_", "defer",
              "all_", "settle", "yield_async"}:
        return (+1, +1, 0, 0, 0, +1)
    if op in {"resolve"}:
        return (+1, +1, +1, +1, 0, +1)
    if op in {"reject", "cancel", "timeout"}:
        return (+1, +1, -1, 0, +1, -1)
    if op in {"catch_", "sync_", "race", "any_of"}:
        return (+1, +1, 0, 0, +1, +1)

    # Event ops: active on KO (intent) + broadcast fan-out
    if op in {"emit", "dispatch", "publish", "signal"}:
        return (+1, +1, +1, +1, 0, +1)
    if op in {"on_", "once_", "listen", "handler", "observer",
              "subject", "stream", "subscribe", "slot", "topic"}:
        return (+1, +1, +1, 0, 0, +1)
    if op in {"off_", "unsubscribe"}:
        return (+1, +1, -1, 0, +1, -1)

    return (0, +1, 0, 0, 0, 0)


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
