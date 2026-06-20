"""Reference template choices for CA opcode semantics.

The emitters need a disciplined place to ask "what semantic template can this
exotic opcode use?" This module is that registry. It is executable in Python so
the choices are testable before they are expanded into every language face.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable, Dict, Iterable, List, Sequence

from .ca_opcode_table import OP_TABLE


@dataclass(frozen=True, slots=True)
class TemplateChoice:
    """A named semantic template available for one or more CA opcodes."""

    name: str
    family: str
    arity: int
    result_shape: str
    portable: bool
    description: str


def _bool(value: object) -> float:
    return 1.0 if bool(value) else 0.0


def _i64(value: float) -> int:
    return int(value) & ((1 << 64) - 1)


def _signed(value: int) -> float:
    value &= (1 << 64) - 1
    if value >= (1 << 63):
        value -= 1 << 64
    return float(value)


def _shift(value: float) -> int:
    return max(0, int(value)) % 64


def _rotl(a: float, b: float) -> float:
    n = _i64(a)
    s = _shift(b)
    return _signed(((n << s) | (n >> (64 - s))) & ((1 << 64) - 1))


def _rotr(a: float, b: float) -> float:
    n = _i64(a)
    s = _shift(b)
    return _signed(((n >> s) | (n << (64 - s))) & ((1 << 64) - 1))


def _clamp(a: float, b: float, c: float) -> float:
    lo, hi = (b, c) if b <= c else (c, b)
    return min(max(a, lo), hi)


def _variance(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)


def _as_values(args: Sequence[float]) -> List[float]:
    return [float(value) for value in args]


def _choice(
    name: str, family: str, arity: int, result_shape: str, description: str
) -> TemplateChoice:
    return TemplateChoice(
        name=name,
        family=family,
        arity=arity,
        result_shape=result_shape,
        portable=True,
        description=description,
    )


SCALAR_FLOAT = _choice(
    "scalar_float", "arithmetic", 2, "float", "Ordinary float stack math."
)
UNARY_FLOAT = _choice("unary_float", "arithmetic", 1, "float", "Unary float transform.")
PREDICATE_01 = _choice(
    "predicate_01", "predicate", 2, "0_or_1", "Boolean result encoded as 1.0 or 0.0."
)
UNARY_PREDICATE_01 = _choice(
    "unary_predicate_01",
    "predicate",
    1,
    "0_or_1",
    "Unary predicate encoded as 1.0 or 0.0.",
)
BITWISE_I64 = _choice(
    "bitwise_i64",
    "bitwise",
    2,
    "i64_as_float",
    "Coerce operands to signed 64-bit integers.",
)
BIT_INDEX_I64 = _choice(
    "bit_index_i64", "bitwise", 2, "i64_as_float", "Use operand b as a 0-63 bit index."
)
UNARY_BITCOUNT_I64 = _choice(
    "unary_bitcount_i64",
    "bitwise",
    1,
    "float",
    "Unary bit inspection on a 64-bit integer.",
)
TERNARY_FLOAT = _choice(
    "ternary_float", "ternary", 3, "float", "Three-input scalar transform."
)
AGGREGATE_SCALAR = _choice(
    "aggregate_scalar",
    "aggregate",
    1,
    "float",
    "Scalar-compatible aggregate: the current stack item is treated as a one-item collection.",
)
PAIR_FOLD = _choice(
    "pair_fold", "aggregate", 2, "float", "Two-input fold/combine template."
)


_OPS: Dict[str, Callable[..., float]] = {
    "add": lambda a, b: a + b,
    "sub": lambda a, b: a - b,
    "mul": lambda a, b: a * b,
    "div": lambda a, b: a / b if b != 0 else 0.0,
    "mod": lambda a, b: a % b if b != 0 else 0.0,
    "pow": lambda a, b: a**b,
    "sqrt": lambda a: math.sqrt(a) if a >= 0 else 0.0,
    "log": lambda a: math.log(a) if a > 0 else 0.0,
    "exp": lambda a: math.exp(a),
    "abs": abs,
    "neg": lambda a: -a,
    "inc": lambda a: a + 1.0,
    "dec": lambda a: a - 1.0,
    "floor": math.floor,
    "ceil": math.ceil,
    "round": round,
    "and": lambda a, b: _bool(a and b),
    "or": lambda a, b: _bool(a or b),
    "not": lambda a: _bool(not a),
    "xor": lambda a, b: _signed(_i64(a) ^ _i64(b)),
    "nand": lambda a, b: _bool(not (a and b)),
    "nor": lambda a, b: _bool(not (a or b)),
    "shl": lambda a, b: _signed(_i64(a) << _shift(b)),
    "shr": lambda a, b: _signed(_i64(a) >> _shift(b)),
    "rotl": _rotl,
    "rotr": _rotr,
    "popcount": lambda a: float(_i64(a).bit_count()),
    "clz": lambda a: 64.0 if _i64(a) == 0 else float(64 - _i64(a).bit_length()),
    "ctz": lambda a: (
        64.0 if _i64(a) == 0 else float((_i64(a) & -_i64(a)).bit_length() - 1)
    ),
    "bitmask": lambda a, b: _signed(_i64(a) & _i64(b)),
    "bitset": lambda a, b: _signed(_i64(a) | (1 << _shift(b))),
    "bitclear": lambda a, b: _signed(_i64(a) & ~(1 << _shift(b))),
    "eq": lambda a, b: _bool(a == b),
    "neq": lambda a, b: _bool(a != b),
    "lt": lambda a, b: _bool(a < b),
    "lte": lambda a, b: _bool(a <= b),
    "gt": lambda a, b: _bool(a > b),
    "gte": lambda a, b: _bool(a >= b),
    "cmp": lambda a, b: -1.0 if a < b else (1.0 if a > b else 0.0),
    "min": min,
    "max": max,
    "clamp": _clamp,
    "within": lambda a, b, c: _bool(min(b, c) <= a <= max(b, c)),
    "isnan": lambda a: _bool(math.isnan(a)),
    "isinf": lambda a: _bool(math.isinf(a)),
    "isfinite": lambda a: _bool(math.isfinite(a)),
    "sign": lambda a: -1.0 if a < 0 else (1.0 if a > 0 else 0.0),
    "classify": lambda a: 3.0 if math.isnan(a) else (2.0 if math.isinf(a) else 1.0),
    "sum": lambda a: a,
    "product": lambda a: a,
    "mean": lambda a: a,
    "variance": lambda a: 0.0,
    "stdev": lambda a: 0.0,
    "reduce": lambda a, b: a + b,
    "fold": lambda a, b: a + b,
    "scan": lambda a, b: a + b,
    "filter": lambda a, b: a if b else 0.0,
    "map": lambda a, b: a + b,
    "zip": lambda a, b: a + b,
    "unzip": lambda a, b: a + b,
    "sort": lambda a: a,
    "unique": lambda a: a,
    "count": lambda a: 1.0,
    "accum": lambda a, b: a + b,
}


_CHOICES: Dict[str, List[TemplateChoice]] = {}


def _assign(names: Iterable[str], *choices: TemplateChoice) -> None:
    for name in names:
        _CHOICES[name] = list(choices)


_assign(["add", "sub", "mul", "div", "mod", "pow"], SCALAR_FLOAT)
_assign(
    ["sqrt", "log", "exp", "abs", "neg", "inc", "dec", "floor", "ceil", "round"],
    UNARY_FLOAT,
)
_assign(
    ["and", "or", "nand", "nor", "eq", "neq", "lt", "lte", "gt", "gte"], PREDICATE_01
)
_assign(["not", "isnan", "isinf", "isfinite"], UNARY_PREDICATE_01)
_assign(["xor", "shl", "shr", "rotl", "rotr", "bitmask"], BITWISE_I64)
_assign(["bitset", "bitclear"], BIT_INDEX_I64)
_assign(["popcount", "clz", "ctz"], UNARY_BITCOUNT_I64)
_assign(["cmp", "min", "max"], SCALAR_FLOAT)
_assign(["clamp", "within"], TERNARY_FLOAT)
_assign(["sign", "classify"], UNARY_FLOAT)
_assign(
    ["sum", "product", "mean", "variance", "stdev", "sort", "unique", "count"],
    AGGREGATE_SCALAR,
)
_assign(["reduce", "fold", "scan", "filter", "map", "zip", "unzip", "accum"], PAIR_FOLD)


def template_choices(op_name: str) -> List[TemplateChoice]:
    """Return the available semantic templates for an opcode name."""

    if op_name not in _CHOICES:
        raise KeyError(f"unknown CA op {op_name!r}")
    return list(_CHOICES[op_name])


def default_choice(op_name: str) -> TemplateChoice:
    """Return the default portable semantic template for an opcode name."""

    return template_choices(op_name)[0]


def opcode_arity(op_name: str) -> int:
    """Return the operand count declared by the CA opcode table."""

    for entry in OP_TABLE.values():
        if entry.name == op_name:
            return max(1, min(3, int(entry.feat[3])))
    raise KeyError(f"unknown CA op {op_name!r}")


def apply_opcode(op_name: str, *args: float, choice: str | None = None) -> float:
    """Apply one CA opcode using a named template choice.

    ``choice`` is checked against the registry so callers cannot accidentally run a
    bitwise op under an aggregate interpretation, or vice versa.
    """

    choices = template_choices(op_name)
    chosen = choice or choices[0].name
    if chosen not in {item.name for item in choices}:
        raise ValueError(f"choice {chosen!r} is not valid for {op_name!r}")
    arity = opcode_arity(op_name)
    if len(args) != arity:
        raise ValueError(f"{op_name} expects {arity} args, got {len(args)}")
    return float(_OPS[op_name](*_as_values(args)))


def run_program(op_names: Sequence[str], args: Sequence[float]) -> float | None:
    """Run CA opcode names against a tiny reference stack machine."""

    stack = [float(arg) for arg in args]
    for op_name in op_names:
        arity = opcode_arity(op_name)
        if len(stack) < arity:
            raise ValueError(
                f"stack underflow at {op_name}: need {arity}, have {len(stack)}"
            )
        operands = stack[-arity:]
        del stack[-arity:]
        stack.append(apply_opcode(op_name, *operands))
    return stack[-1] if stack else None


def coverage_report() -> dict:
    """Return a compact report proving every CA opcode has at least one choice."""

    covered = sorted(_CHOICES)
    missing = sorted(
        entry.name for entry in OP_TABLE.values() if entry.name not in _CHOICES
    )
    return {
        "covered": len(covered),
        "missing": missing,
        "families": sorted(
            {choice.family for choices in _CHOICES.values() for choice in choices}
        ),
    }


__all__ = [
    "TemplateChoice",
    "apply_opcode",
    "coverage_report",
    "default_choice",
    "opcode_arity",
    "run_program",
    "template_choices",
]
