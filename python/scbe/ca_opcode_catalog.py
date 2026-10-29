"""Dependency-free Cassisivadan opcode names.

This module is intentionally limited to the Python standard library.  Small
tools such as ``scbe ca-plan`` can load the opcode/name mapping without
initializing the numerical SCBE runtime (and therefore without requiring
NumPy).  ``ca_opcode_table`` verifies that its rich numerical table stays in
lockstep with this catalog.
"""

from __future__ import annotations

CA_OPCODE_NAMES: tuple[str, ...] = (
    # 0x00-0x0F: arithmetic
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
    # 0x10-0x1F: logic
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
    # 0x20-0x2F: comparison
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
    # 0x30-0x3F: aggregation
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
)

if len(CA_OPCODE_NAMES) != 64 or len(set(CA_OPCODE_NAMES)) != 64:
    raise RuntimeError("CA opcode catalog must contain 64 unique names")

CA_OPCODE_BY_NAME: dict[str, int] = {name: op_id for op_id, name in enumerate(CA_OPCODE_NAMES)}

__all__ = ["CA_OPCODE_NAMES", "CA_OPCODE_BY_NAME"]
