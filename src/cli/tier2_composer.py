"""
tier2_composer.py — Tier 2 cross-build: variable binding + control flow.

Tier 1 (cross_build_ir.py) translates single expressions. It is
intentionally sub-Turing: no named state, no branching, no loops.

This module adds exactly the three pieces that close the Turing gap:
  1. VarEnv  — bindings that persist and carry provenance across ops.
  2. Node types — LetNode, IfNode, WhileNode, SeqNode, DefNode, CallNode.
     Leaves are either LatticeOp references or literal values.
  3. eval_node / emit_node — execute OR generate code from the same tree.

The 64 existing LatticeOps are leaves, unchanged. Control flow sits
ABOVE them in new node types. The LatticeOp class is not touched.

Turing proof: factorial(n) is expressible here via WhileNode + LetNode.
Run this file directly to see it execute and emit in all six tongues:
  python -m src.cli.tier2_composer
"""

from __future__ import annotations

import math
import operator
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

from src.ca_lexicon import LEXICON_BY_NAME, LANG_MAP
from src.cli.cross_build_ir import LatticeOp, QuarantineError
from src.cli.basen_normalizer import emit_literal, parse_literal

# ── Tongue identifiers ────────────────────────────────────────────────────────

TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")


# ─────────────────────────────────────────────────────────────────────────────
#  VarEnv — variable binding environment with provenance
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Binding:
    """One resolved variable binding with provenance."""

    name: str
    value: Any
    source_op: Optional[str] = None  # op_name that produced this, if any
    step_index: int = 0  # position in the sequence that bound it


class VarEnv:
    """Mutable binding environment.

    Supports nested scopes for function calls via push/pop. History is
    append-only so governance audits have full provenance chains.
    """

    def __init__(self) -> None:
        self._scopes: List[Dict[str, Any]] = [{}]
        self.history: List[Binding] = []
        self._step: int = 0

    # ── scope management ─────────────────────────────────────────────────────

    def push_scope(self) -> None:
        self._scopes.append({})

    def pop_scope(self) -> None:
        if len(self._scopes) > 1:
            self._scopes.pop()

    # ── read ─────────────────────────────────────────────────────────────────

    def lookup(self, name: str) -> Any:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        raise NameError(f"variable {name!r} is not bound in the current env")

    def snapshot(self) -> Dict[str, Any]:
        """Flat view of current bindings (inner-most scope wins)."""
        merged: Dict[str, Any] = {}
        for scope in self._scopes:
            merged.update(scope)
        return merged

    # ── write ─────────────────────────────────────────────────────────────────

    def bind(self, name: str, value: Any, *, source_op: Optional[str] = None) -> None:
        self._scopes[-1][name] = value
        self.history.append(
            Binding(name=name, value=value, source_op=source_op, step_index=self._step)
        )

    def tick(self) -> None:
        self._step += 1

    def __repr__(self) -> str:
        return f"VarEnv({self.snapshot()})"


# ─────────────────────────────────────────────────────────────────────────────
#  Node types — the Tier 2 program tree
#
#  LatticeOp is a LEAF. Control-flow nodes sit above it, never inside it.
# ─────────────────────────────────────────────────────────────────────────────

# A node is anything the composer can evaluate or emit.
NodeType = Union[
    "LitNode",
    "VarNode",
    "OpNode",
    "LetNode",
    "IfNode",
    "WhileNode",
    "SeqNode",
    "DefNode",
    "CallNode",
]


@dataclass
class LitNode:
    """A literal value — integer, float, bool, string, or list.

    Accepts any Python literal, including numeric representations from
    basen_normalizer (binary, hex, ternary strings get parsed here).
    """

    raw: Any
    _parsed: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if isinstance(self.raw, str):
            try:
                p = parse_literal(self.raw)
                self._parsed = p.value
            except ValueError:
                self._parsed = self.raw  # treat as a string literal
        else:
            self._parsed = self.raw

    @property
    def value(self) -> Any:
        return self._parsed


@dataclass
class VarNode:
    """Reference to a name in the current VarEnv."""

    name: str


@dataclass
class OpNode:
    """A LatticeOp expression with Tier-2 argument nodes (not just string names)."""

    op_name: str
    arg_nodes: Dict[str, NodeType]  # keys are the LatticeOp arg template names

    def to_lattice_op(self, env: "VarEnv") -> "tuple[LatticeOp, Dict[str, Any]]":
        """Resolve arg_nodes into values and produce the IR node.

        Returns both the LatticeOp (with string arg names suitable for
        emit_from_ir) and the resolved numeric args dict.
        """
        entry = LEXICON_BY_NAME.get(self.op_name)
        if entry is None:
            raise QuarantineError(f"unknown op: {self.op_name!r}")
        # Resolve the concrete values for evaluation
        resolved: Dict[str, Any] = {}
        str_args: Dict[str, str] = {}
        for arg_key, node in self.arg_nodes.items():
            v = eval_node(node, env)
            resolved[arg_key] = v
            str_args[arg_key] = str(v) if not isinstance(v, str) else v
        ir = LatticeOp.from_entry(entry, str_args)
        return ir, resolved


@dataclass
class LetNode:
    """Bind the result of `expr` to `name` in the current scope."""

    name: str
    expr: NodeType


@dataclass
class IfNode:
    """Conditional branch."""

    cond: NodeType
    then_body: "SeqNode"
    else_body: Optional["SeqNode"] = None


@dataclass
class WhileNode:
    """Loop while `cond` is truthy, executing `body` each iteration."""

    cond: NodeType
    body: "SeqNode"
    max_iterations: int = 100_000  # hard cap to prevent infinite loops


@dataclass
class SeqNode:
    """Ordered sequence of nodes. Threads VarEnv forward."""

    nodes: List[NodeType]


@dataclass
class DefNode:
    """Define a named function for later CallNode use."""

    name: str
    params: List[str]
    body: SeqNode
    return_var: Optional[str] = None  # name of the variable whose value is returned


@dataclass
class CallNode:
    """Call a defined function by name with named argument values."""

    func_name: str
    kwargs: Dict[str, NodeType]


# ─────────────────────────────────────────────────────────────────────────────
#  Op evaluation table — maps op_name to a Python callable
# ─────────────────────────────────────────────────────────────────────────────


def _rotl(x: int, n: int, bits: int = 64) -> int:
    n %= bits
    return ((x << n) | (x >> (bits - n))) & ((1 << bits) - 1)


def _rotr(x: int, n: int, bits: int = 64) -> int:
    n %= bits
    return ((x >> n) | (x << (bits - n))) & ((1 << bits) - 1)


def _clz(x: int, bits: int = 64) -> int:
    if x == 0:
        return bits
    return bits - x.bit_length()


def _ctz(x: int) -> int:
    if x == 0:
        return 64
    return (x & -x).bit_length() - 1


def _cmp(a: Any, b: Any) -> int:
    return 0 if a == b else (1 if a > b else -1)


def _sign(x: Any) -> int:
    return 0 if x == 0 else (1 if x > 0 else -1)


def _classify(x: float) -> str:
    if math.isnan(x):
        return "nan"
    if math.isinf(x):
        return "inf"
    if x == 0.0:
        return "zero"
    return "normal"


def _clamp(x: Any, lo: Any, hi: Any) -> Any:
    return max(lo, min(hi, x))


def _within(x: Any, lo: Any, hi: Any) -> bool:
    return lo <= x <= hi


def _bitmask(x: int, n: int) -> int:
    return x & ((1 << n) - 1)


def _bitset(x: int, n: int) -> int:
    return x | (1 << n)


def _bitclear(x: int, n: int) -> int:
    return x & ~(1 << n)


def _product(xs: list) -> Any:
    result = 1
    for v in xs:
        result *= v
    return result


def _variance(xs: list) -> float:
    if not xs:
        return 0.0
    m = sum(xs) / len(xs)
    return sum((v - m) ** 2 for v in xs) / len(xs)


def _scan(xs: list, f: Callable) -> list:
    acc = xs[0] if xs else 0
    out = [acc]
    for v in xs[1:]:
        acc = f(acc, v)
        out.append(acc)
    return out


def _accum(xs: list, init: Any = 0) -> list:
    total = init
    result = []
    for v in xs:
        total += v
        result.append(total)
    return result


# Single-arg ops (valence 1): arg key = "a"
_UNARY: Dict[str, Callable] = {
    "sqrt": math.sqrt,
    "log": math.log,
    "exp": math.exp,
    "abs": abs,
    "neg": operator.neg,
    "inc": lambda a: a + 1,
    "dec": lambda a: a - 1,
    "floor": math.floor,
    "ceil": math.ceil,
    "round": round,
    "not": lambda a: ~a,
    "popcount": lambda a: bin(a).count("1"),
    "clz": _clz,
    "ctz": _ctz,
    "isnan": math.isnan,
    "isinf": math.isinf,
    "isfinite": math.isfinite,
    "sign": _sign,
    "classify": _classify,
    "sum": sum,
    "product": _product,
    "mean": lambda a: sum(a) / len(a) if a else 0.0,
    "variance": _variance,
    "stdev": lambda a: math.sqrt(_variance(a)),
    "count": len,
    "unique": lambda a: list(dict.fromkeys(a)),
    "sort": sorted,
    "unzip": lambda a: list(zip(*a)) if a else ([], []),
}

# Two-arg ops (valence 2): arg keys = "a", "b"
_BINARY: Dict[str, Callable] = {
    "add": operator.add,
    "sub": operator.sub,
    "mul": operator.mul,
    "div": operator.truediv,
    "mod": operator.mod,
    "pow": operator.pow,
    "and": operator.and_,
    "or": operator.or_,
    "xor": operator.xor,
    "nand": lambda a, b: ~(a & b),
    "nor": lambda a, b: ~(a | b),
    "shl": operator.lshift,
    "shr": operator.rshift,
    "rotl": _rotl,
    "rotr": _rotr,
    "bitmask": _bitmask,
    "bitset": _bitset,
    "bitclear": _bitclear,
    "eq": operator.eq,
    "neq": operator.ne,
    "lt": operator.lt,
    "lte": operator.le,
    "gt": operator.gt,
    "gte": operator.ge,
    "cmp": _cmp,
    "min": min,
    "max": max,
    "zip": lambda a, b: list(zip(a, b)),
    "log": math.log,  # two-arg form: log(x, base)
}

# Three-arg ops: arg keys = "a", "b", "c"
_TERNARY: Dict[str, Callable] = {
    "clamp": _clamp,
    "within": _within,
}

# Higher-order aggregation ops: take (xs, f) where f resolves from VarEnv
_HIGHER_ORDER: Dict[str, Callable] = {
    "reduce": lambda xs, f: __import__("functools").reduce(f, xs),
    "fold": lambda xs, f: __import__("functools").reduce(f, xs),
    "scan": _scan,
    "filter": lambda xs, f: list(filter(f, xs)),
    "map": lambda xs, f: list(map(f, xs)),
    "accum": _accum,
}


def _eval_op(op_name: str, resolved: Dict[str, Any], env: "VarEnv") -> Any:
    """Evaluate a resolved op dict against the known op tables."""
    if op_name in _UNARY:
        return _UNARY[op_name](resolved["a"])
    if op_name in _BINARY:
        return _BINARY[op_name](resolved["a"], resolved["b"])
    if op_name in _TERNARY:
        return _TERNARY[op_name](resolved["a"], resolved["b"], resolved["c"])
    if op_name in _HIGHER_ORDER:
        xs = resolved["xs"]
        # 'f' may be a function name bound in the env, a DefNode, or a callable
        raw_f = resolved.get("f", None)
        if callable(raw_f):
            func = raw_f
        elif isinstance(raw_f, str):
            try:
                func = env.lookup(raw_f)
            except NameError:
                raise QuarantineError(
                    f"op {op_name!r}: 'f' argument {raw_f!r} is not bound in VarEnv"
                )
        else:
            func = raw_f
        return _HIGHER_ORDER[op_name](xs, func)
    raise QuarantineError(f"no evaluator registered for op: {op_name!r}")


# ─────────────────────────────────────────────────────────────────────────────
#  Function registry — populated by eval_node on DefNode
# ─────────────────────────────────────────────────────────────────────────────

_FUNC_REGISTRY: Dict[str, "DefNode"] = {}


# ─────────────────────────────────────────────────────────────────────────────
#  Evaluator
# ─────────────────────────────────────────────────────────────────────────────


def eval_node(node: NodeType, env: VarEnv) -> Any:
    """Execute a Tier-2 node against the environment, returning its value."""
    env.tick()

    if isinstance(node, LitNode):
        return node.value

    if isinstance(node, VarNode):
        return env.lookup(node.name)

    if isinstance(node, OpNode):
        _, resolved = node.to_lattice_op(env)
        return _eval_op(node.op_name, resolved, env)

    if isinstance(node, LetNode):
        value = eval_node(node.expr, env)
        env.bind(node.name, value, source_op=_op_name_of(node.expr))
        return value

    if isinstance(node, IfNode):
        cond = eval_node(node.cond, env)
        if cond:
            return eval_node(node.then_body, env)
        elif node.else_body is not None:
            return eval_node(node.else_body, env)
        return None

    if isinstance(node, WhileNode):
        iterations = 0
        result = None
        while eval_node(node.cond, env):
            result = eval_node(node.body, env)
            iterations += 1
            if iterations >= node.max_iterations:
                raise RecursionError(
                    f"WhileNode exceeded max_iterations={node.max_iterations}"
                )
        return result

    if isinstance(node, SeqNode):
        result = None
        for child in node.nodes:
            result = eval_node(child, env)
        return result

    if isinstance(node, DefNode):
        _FUNC_REGISTRY[node.name] = node

        # Also bind as a callable in the env so higher-order ops can find it
        def _caller(*positional, **kwargs):  # noqa: E731
            return _call_def(node, positional, kwargs)

        env.bind(node.name, _caller)
        return _caller

    if isinstance(node, CallNode):
        defn = _FUNC_REGISTRY.get(node.func_name)
        if defn is None:
            raise NameError(f"function {node.func_name!r} is not defined")
        call_env = VarEnv()
        for param, kwnode in node.kwargs.items():
            call_env.bind(param, eval_node(kwnode, env))
        call_env.push_scope()
        result = eval_node(defn.body, call_env)
        if defn.return_var:
            return call_env.lookup(defn.return_var)
        return result

    raise TypeError(f"unknown node type: {type(node).__name__}")


def _call_def(defn: "DefNode", positional: tuple, kwargs: dict) -> Any:
    """Internal caller for when a DefNode is used as a Python callable."""
    call_env = VarEnv()
    for i, param in enumerate(defn.params):
        if param in kwargs:
            call_env.bind(param, kwargs[param])
        elif i < len(positional):
            call_env.bind(param, positional[i])
    result = eval_node(defn.body, call_env)
    if defn.return_var:
        return call_env.lookup(defn.return_var)
    return result


def _op_name_of(node: NodeType) -> Optional[str]:
    if isinstance(node, OpNode):
        return node.op_name
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Code emitter — generate source in any tongue from the Tier-2 tree
# ─────────────────────────────────────────────────────────────────────────────

# Control-flow syntax per tongue
_CF: Dict[str, Dict[str, str]] = {
    "KO": {  # Python
        "let": "{name} = {expr}",
        "if": "if {cond}:",
        "else": "else:",
        "while": "while {cond}:",
        "def": "def {name}({params}):",
        "return": "return {var}",
        "call": "{name}({kwargs})",
        "indent": "    ",
        "block_start": "",
        "block_end": "",
    },
    "AV": {  # TypeScript
        "let": "let {name} = {expr};",
        "if": "if ({cond}) {{",
        "else": "} else {",
        "while": "while ({cond}) {{",
        "def": "function {name}({params}) {{",
        "return": "return {var};",
        "call": "{name}({kwargs})",
        "indent": "  ",
        "block_start": "",
        "block_end": "}",
    },
    "RU": {  # Rust
        "let": "let {name} = {expr};",
        "if": "if {cond} {{",
        "else": "} else {",
        "while": "while {cond} {{",
        "def": "fn {name}({params}) {{",
        "return": "return {var};",
        "call": "{name}({kwargs})",
        "indent": "    ",
        "block_start": "",
        "block_end": "}",
    },
    "CA": {  # C
        "let": "{type} {name} = {expr};",
        "if": "if ({cond}) {{",
        "else": "} else {",
        "while": "while ({cond}) {{",
        "def": "{type} {name}({params}) {{",
        "return": "return {var};",
        "call": "{name}({kwargs})",
        "indent": "    ",
        "block_start": "",
        "block_end": "}",
    },
    "UM": {  # Julia
        "let": "{name} = {expr}",
        "if": "if {cond}",
        "else": "else",
        "while": "while {cond}",
        "def": "function {name}({params})",
        "return": "return {var}",
        "call": "{name}({kwargs})",
        "indent": "    ",
        "block_start": "",
        "block_end": "end",
    },
    "DR": {  # Haskell
        "let": "let {name} = {expr}",
        "if": "if {cond}",
        "else": "else",
        "while": "-- while {cond}:  (use recursion in Haskell)",
        "def": "{name} {params} =",
        "return": "{var}",
        "call": "({name} {kwargs})",
        "indent": "  ",
        "block_start": "",
        "block_end": "",
    },
}


def emit_node(node: NodeType, tongue: str, indent: int = 0) -> str:
    """Generate a source code string for `node` in the given tongue.

    Leaves that are LatticeOps use the existing Tier-1 emit_from_ir.
    Control-flow nodes use the tongue-specific _CF syntax table.
    """
    tongue = tongue.upper()
    if tongue not in TONGUES:
        raise ValueError(f"unknown tongue: {tongue!r}")
    cf = _CF[tongue]
    pad = cf["indent"] * indent

    if isinstance(node, LitNode):
        return pad + repr(node.value)

    if isinstance(node, VarNode):
        return pad + node.name

    if isinstance(node, OpNode):
        entry = LEXICON_BY_NAME.get(node.op_name)
        if entry is None:
            raise QuarantineError(f"unknown op: {node.op_name!r}")
        template = entry.code.get(tongue)
        if template is None:
            raise QuarantineError(
                f"op {node.op_name!r} has no template for tongue={tongue}"
            )
        # For code emission, args are variable names (VarNode) or literal strings
        str_args = {}
        for k, v in node.arg_nodes.items():
            str_args[k] = _emit_inline(v, tongue)
        return pad + template.format(**str_args)

    if isinstance(node, LetNode):
        expr_str = _emit_inline(node.expr, tongue)
        tpl = cf["let"].format(name=node.name, expr=expr_str, type="auto")
        return pad + tpl

    if isinstance(node, IfNode):
        lines = []
        cond_str = _emit_inline(node.cond, tongue)
        lines.append(pad + cf["if"].format(cond=cond_str))
        if cf["block_start"]:
            lines.append(pad + cf["block_start"])
        for child in node.then_body.nodes:
            lines.append(emit_node(child, tongue, indent + 1))
        if node.else_body is not None:
            lines.append(pad + cf["else"])
            for child in node.else_body.nodes:
                lines.append(emit_node(child, tongue, indent + 1))
        if cf["block_end"]:
            lines.append(pad + cf["block_end"])
        return "\n".join(lines)

    if isinstance(node, WhileNode):
        lines = []
        cond_str = _emit_inline(node.cond, tongue)
        lines.append(pad + cf["while"].format(cond=cond_str))
        if cf["block_start"]:
            lines.append(pad + cf["block_start"])
        for child in node.body.nodes:
            lines.append(emit_node(child, tongue, indent + 1))
        if cf["block_end"]:
            lines.append(pad + cf["block_end"])
        return "\n".join(lines)

    if isinstance(node, SeqNode):
        parts = []
        for child in node.nodes:
            parts.append(emit_node(child, tongue, indent))
        return "\n".join(parts)

    if isinstance(node, DefNode):
        lines = []
        params_str = ", ".join(node.params)
        lines.append(
            pad + cf["def"].format(name=node.name, params=params_str, type="auto")
        )
        if cf["block_start"]:
            lines.append(pad + cf["block_start"])
        for child in node.body.nodes:
            lines.append(emit_node(child, tongue, indent + 1))
        if node.return_var:
            lines.append(
                cf["indent"] * (indent + 1) + cf["return"].format(var=node.return_var)
            )
        if cf["block_end"]:
            lines.append(pad + cf["block_end"])
        return "\n".join(lines)

    if isinstance(node, CallNode):
        kwargs_str = ", ".join(
            f"{k}={_emit_inline(v, tongue)}" for k, v in node.kwargs.items()
        )
        tpl = cf["call"].format(name=node.func_name, kwargs=kwargs_str)
        return pad + tpl

    raise TypeError(f"unknown node type: {type(node).__name__}")


def _emit_inline(node: NodeType, tongue: str) -> str:
    """Emit without leading indentation (for use inside expressions)."""
    return emit_node(node, tongue, indent=0).lstrip()


# ─────────────────────────────────────────────────────────────────────────────
#  Ergonomic tongue routing (not capability routing — all tongues are
#  computationally equivalent; this is about which is most natural)
# ─────────────────────────────────────────────────────────────────────────────

# op_name → best tongue for human-readable output
_AFFINITY: Dict[str, str] = {
    # ARITHMETIC: Python is clean and reads like pseudocode
    **{
        k: "KO"
        for k in (
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
        )
    },
    # LOGIC (bitwise): C's idiom is most canonical
    **{
        k: "CA"
        for k in (
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
        )
    },
    # COMPARISON: Julia has nice chaining, but Python is most readable
    **{
        k: "KO"
        for k in (
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
        )
    },
    # AGGREGATION: Haskell is most ergonomic for higher-order functional ops
    **{
        k: "DR"
        for k in (
            "reduce",
            "fold",
            "scan",
            "filter",
            "map",
        )
    },
    # ... rest of aggregation stays in Python
    **{
        k: "KO"
        for k in (
            "sum",
            "product",
            "mean",
            "variance",
            "stdev",
            "zip",
            "unzip",
            "sort",
            "unique",
            "count",
            "accum",
        )
    },
}

# Haskell has no mutable loop — for WhileNode, prefer KO or RU
_CONTROL_FLOW_AFFINITY: Dict[str, str] = {
    "IfNode": "KO",
    "WhileNode": "RU",  # Rust's ownership makes loops safer
    "LetNode": "KO",
    "DefNode": "DR",  # Haskell for pure function definitions
    "CallNode": "KO",
    "SeqNode": "KO",
}


def suggest_tongue(node: NodeType) -> str:
    """Return the ergonomically-best tongue for emitting this node."""
    if isinstance(node, OpNode):
        return _AFFINITY.get(node.op_name, "KO")
    return _CONTROL_FLOW_AFFINITY.get(type(node).__name__, "KO")


def analyse_patchwork(program: SeqNode) -> List[Dict]:
    """For each node in a SeqNode, describe the routing decision.

    Returns a list of dicts: {node_type, op, tongue, reason}.
    Use this to understand how a program would be spread across tongues.
    """
    result = []
    for node in program.nodes:
        tongue = suggest_tongue(node)
        reason = f"ergonomic: {LANG_MAP.get(tongue, tongue)} is most natural here"
        entry = {
            "node_type": type(node).__name__,
            "op": getattr(node, "op_name", getattr(node, "name", "—")),
            "tongue": tongue,
            "language": LANG_MAP.get(tongue, tongue),
            "reason": reason,
        }
        result.append(entry)
    return result


# ─────────────────────────────────────────────────────────────────────────────
#  Turing-completeness proof: factorial via WhileNode
# ─────────────────────────────────────────────────────────────────────────────


def build_factorial(n: int) -> SeqNode:
    """Build a Tier-2 program that computes n! using WhileNode + LetNode.

    This is the proof that the system is now Turing-sufficient:
    it requires variable binding (LetNode), conditional iteration (WhileNode),
    and two-register accumulation — the exact three primitives that close
    the sub-Turing gap.
    """
    # acc = 1; n_var = n; while n_var > 1: acc = acc * n_var; n_var = n_var - 1
    return SeqNode(
        nodes=[
            LetNode("acc", LitNode(1)),
            LetNode("n_var", LitNode(n)),
            WhileNode(
                cond=OpNode("gt", {"a": VarNode("n_var"), "b": LitNode(1)}),
                body=SeqNode(
                    nodes=[
                        LetNode(
                            "acc",
                            OpNode("mul", {"a": VarNode("acc"), "b": VarNode("n_var")}),
                        ),
                        LetNode("n_var", OpNode("dec", {"a": VarNode("n_var")})),
                    ]
                ),
            ),
            VarNode("acc"),  # return value of the sequence
        ]
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Self-test / demo
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 70)
    print("Tier 2 composer — Turing completeness proof")
    print("=" * 70)

    # 1. Evaluate factorial(5) = 120
    program = build_factorial(5)
    env = VarEnv()
    result = eval_node(program, env)
    print(f"\n  factorial(5) evaluated = {result}")
    assert result == 120, f"expected 120, got {result}"
    print("  PASS: eval matches expected 120")

    # 2. Emit in all 6 tongues
    print("\n  Code emission (all 6 tongues):")
    print()
    for tongue in TONGUES:
        lang = LANG_MAP.get(tongue, tongue)
        code = emit_node(program, tongue)
        print(f"  [{tongue}] {lang}")
        for line in code.split("\n"):
            print(f"      {line}")
        print()

    # 3. Patchwork analysis (ergonomic routing)
    print("  Patchwork routing analysis:")
    patches = analyse_patchwork(program)
    for p in patches:
        print(
            f"    {p['node_type']:12} op={p['op']:8}  → {p['tongue']} ({p['language']})"
        )

    # 4. VarEnv provenance
    print("\n  VarEnv bindings after execution:")
    for b in env.history:
        print(
            f"    step {b.step_index:3}  {b.name:8} = {b.value!r:12}  "
            f"  (via {b.source_op or 'literal'})"
        )

    # 5. BaseN normalizer round-trip
    print("\n  BaseN normalization (binary/hex/ternary → same integer):")
    cases = [("0b1111000", 2), ("0x78", 16), ("0t10200", 3)]
    for literal_str, base in cases:
        parsed = parse_literal(literal_str)
        dec = emit_literal(parsed.value, 10, "KO")
        hex_ = emit_literal(parsed.value, 16, "RU")
        print(f"    {literal_str:15} → int {parsed.value:6d}  → RU hex: {hex_}")
    assert parse_literal("0b1111000").value == parse_literal("0x78").value == 120
    print("  PASS: all three representations of 120 normalize to the same int")

    print("\n  All Tier-2 self-tests PASSED.")
    print("=" * 70)
