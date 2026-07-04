"""
Polyglot stack-machine emitter — one core, every language face.
====================================================================

The cube: the CENTER is the binary/trit core (bit_spine) + the CA 64-opcode
table (ca_opcode_table). Each FACE is a programming language. This module emits
a CA opcode program to source for registered dialects that implement the requested
ops. Registered is not the same as fully verified: bundled dialects can be
emit-only until a local toolchain proves them.

Unlike tongue_isa (which bakes a field per language into every opcode), each
language here is a pure DATA `Dialect` — a registry entry. Adding a language is
one independent track: fill a Dialect literal, register it. Nothing else changes.

Conformance is checked by polyglot_conformance.py: it compiles+runs each backend that has
a LOCAL toolchain (python in-process, javascript via node, rust via rustc) and reports the
rest as emitted-but-unverified -- never as agreement. "Compiles no matter what" means the
emitter PRODUCES source for every backend; it does NOT mean the backends compute identical
results -- where they would diverge, the harness surfaces it as DISAGREE rather than hiding.
The known cross-language splits on the EXECUTED faces (py/js/rust) have since been UNIFIED to
the Python reference and verified on adversarial inputs: round -> half-to-even (round_ties_even
/ banker's helper); mod -> floored (a - b*floor(a/b), matches Python's sign-of-divisor); pow ->
the negative-base/non-integer-exponent intersection roundabouts to 0.0 in all faces (like
sqrt-of-negative); div is portable. Emit-only faces (c/cpp/go/java/...) still use native
semantics and would need the same helpers before joining the executed gate.

Two op sets, kept distinct on purpose:
  * SCALAR_OPS   (22) -- the original cube/DNA core. It is the intended baseline for registered
                         language faces; emit still checks each dialect and fails closed if a face is
                         missing a template.
  * PORTABLE_OPS (35) -- the conformance-checked polyglot-emitter subset for implemented dialects.
                         Extension ops have been checked across the local executable backends
                         (python/js/rust/c when available); missing toolchains or missing dialect
                         templates are not counted as agreement.

The simplest commands are the bit/byte primitives, and they map across languages the most cleanly --
so the bitwise ops are the load-bearing extension:
  bitwise      and or xor not shl shr                           (INTEGER: operands truncated to int;
                 portable on the 32-bit SIGNED domain |x| < 2^31 -- BEYOND it JS uses int32 and the
                 harness reports DISAGREE. That boundary is the honest limit, surfaced not hidden.
                 shl/shr shift counts must be >= 0; the C face casts to `long long` to match Rust i64.)
  arithmetic   add sub mul div mod neg inc dec
  math fns     pow abs sqrt floor ceil round min max  log exp   (log: x>0 -- safe-mode roundabout maps
                 x<=0 -> 0.0, exactly like sqrt; exp: verified on non-overflowing x (no roundabout,
                 raises in unsafe mode on overflow, as any face would). Verified on the valid domain.)
  sign/cmp     sign cmp                                          (-> -1.0 / 0.0 / 1.0)
  comparison   eq neq lt lte gt gte                              (-> 1.0 / 0.0, keeps the number stack)
  predicates   isnan isinf isfinite                             (-> 1.0 / 0.0; verified on nan/inf too)
The remaining CA ops (rotl/rotr/popcount/..., aggregation sum/reduce/sort/...) are NOT yet portable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

from .ca_opcode_table import OP_TABLE

# op_name -> op_byte (first occurrence wins)
NAME_TO_BYTE: Dict[str, int] = {}
for _b, _e in OP_TABLE.items():
    NAME_TO_BYTE.setdefault(_e.name, _b)
BYTE_TO_NAME: Dict[int, str] = {b: e.name for b, e in OP_TABLE.items()}

# --- op categories (language-agnostic) -----------------------------------
BINOPS = {"add": "+", "sub": "-", "mul": "*", "div": "/"}
CMPS = {"eq": "==", "neq": "!=", "lt": "<", "lte": "<=", "gt": ">", "gte": ">="}
# The ORIGINAL cube/DNA core (which the DNA-bijection in bijective_dna is built over).
# A dialect is still checked at emit time; "in the core" does not bypass missing templates.
_CORE_FUNC2 = {"pow", "min", "max", "mod"}
_CORE_FUNC1 = {"neg", "abs", "sqrt", "floor", "ceil", "round", "inc", "dec"}
# The VERIFIED-PORTABLE EXTENSION -- proven identical across python/js/rust by polyglot_conformance,
# implemented (so far) by the inline faces. cmp = spaceship (-1/0/1); and/or/xor = INTEGER bitwise
# (operands truncated to int; portable on the 32-bit signed domain, see the conformance note); sign =
# -1/0/1; log/exp on their natural domain; isnan/isinf/isfinite = 1.0/0.0 predicates.
_EXT_FUNC2 = {"cmp", "and", "or", "xor", "shl", "shr"}
_EXT_FUNC1 = {"sign", "log", "exp", "isnan", "isinf", "isfinite", "not"}

FUNC2 = _CORE_FUNC2 | _EXT_FUNC2
FUNC1 = _CORE_FUNC1 | _EXT_FUNC1

# SCALAR_OPS = the original cube/DNA core (22): the bijection covers it, and emit verifies dialect support.
SCALAR_OPS = set(BINOPS) | set(CMPS) | _CORE_FUNC2 | _CORE_FUNC1
# PORTABLE_OPS = the conformance-checked polyglot-emitter subset (35): emittable for registered dialects
# that implement the op, with agreement checked only on local executable backends.
PORTABLE_OPS = set(BINOPS) | set(CMPS) | FUNC2 | FUNC1


def _dialect_supports(d: "Dialect", name: str) -> bool:
    """Does this language face implement `name`? Operators (BINOPS/CMPS) are universal; FUNC1/FUNC2
    ops need a per-dialect template. Lets `emit` raise a clear 'not implemented in this face' error
    instead of a raw KeyError when a newer op outruns an older dialect."""
    if name in BINOPS or name in CMPS:
        return True
    if name in FUNC1:
        return name in d.func1
    if name in FUNC2:
        return name in d.func2
    return False


def _sub(tmpl: str, **kw: object) -> str:
    """Substitute {key} placeholders, leaving literal braces (JS/C/Rust) intact."""
    out = tmpl
    for k, v in kw.items():
        out = out.replace("{" + k + "}", str(v))
    return out


@dataclass(frozen=True)
class Dialect:
    """One language face — pure data, no per-opcode code."""

    name: str
    ext: str
    comment: str  # "#" | "//" | "--"
    indent: str
    prelude: Tuple[str, ...]  # module-level imports / helpers
    fn_open: str  # "{fn}({params})" frame, e.g. "def {fn}({params}):"
    stack_init: str  # "{init}" -> declare stack seeded with args
    pop2: str  # statement binding a, b off the stack
    pop1: str  # statement binding a off the stack
    push: str  # "{expr}" -> push expr onto the stack
    ret: str  # return top of stack
    fn_close: Tuple[str, ...]  # closing lines (braces etc.)
    func1: Dict[str, str]  # unary: "{a}" -> expr
    func2: Dict[str, str]  # binary: "{a}","{b}" -> expr
    binop_over: Dict[str, str] = field(default_factory=dict)  # op_name -> override operator
    cmp_over: Dict[str, str] = field(default_factory=dict)  # cmp_name -> override (Lua "~=", Haskell "/=")
    cmp_tmpl: str = "(1.0 if {cond} else 0.0)"  # ternary keeping number stack
    main_tmpl: Tuple[str, ...] = ()  # optional runnable main(); {fn} placeholder
    var_a: str = "a"  # temp-var name the push expr uses; sigil langs override (PHP: "$a")
    var_b: str = "b"  # second-operand temp-var name; must match what pop2 binds


def _ternary(d: Dialect) -> str:
    """A general select(cond,t,f) derived from the dialect's own comparison template
    (its cmp_tmpl already encodes the language's ternary, mapping a bool to 1.0/0.0)."""
    t = d.cmp_tmpl.replace("1.0", "{t}").replace("0.0", "{f}")
    if "{t}" not in t or "{f}" not in t:
        t = "({cond} ? {t} : {f})"  # fallback for an unusual dialect
    return t


# ROUNDABOUTS: the undefined intersections (div 0, sqrt of a negative) defined as
# CODE NODES -- a chosen, consistent handler emitted identically into every
# language so traffic routes around instead of crashing (py raises / js NaN).
#   div/mod by zero -> 0.0 ;  sqrt of negative -> 0.0
def _render(name: str, d: Dialect, safe: bool = False) -> Tuple[str, bool]:
    """Return (push-expression using the dialect's temp var names, is_binary)."""
    va, vb = d.var_a, d.var_b  # "a"/"b" everywhere except sigil langs (PHP: "$a"/"$b")
    if name in BINOPS:
        op = d.binop_over.get(name, BINOPS[name])
        expr = f"{va} {op} {vb}"
        if safe and name == "div":
            expr = _sub(_ternary(d), cond=f"{vb} == 0.0", t="0.0", f=f"{va} / {vb}")
        return expr, True
    if name in CMPS:
        # NOTE: `round` (FUNC1) is UNIFIED to Python's round-half-to-even (banker's) across the
        # executed faces: Rust uses round_ties_even(); JS uses the _round_ties_even() prelude helper;
        # Python's round() is already half-to-even. So py/js/rust now AGREE on exact .5 values (the
        # former known divergence). Untested emit-only faces (c/cpp/go/java/...) still use native
        # rounding and would need the same helper before they can be added to the executed gate.
        op = d.cmp_over.get(name, CMPS[name])
        return _sub(d.cmp_tmpl, cond=f"{va} {op} {vb}"), True
    if name in FUNC2:
        expr = _sub(d.func2[name], a=va, b=vb)
        if safe and name == "mod":
            expr = _sub(_ternary(d), cond=f"{vb} == 0.0", t="0.0", f=expr)
        if safe and name == "pow":
            # Undefined intersection: negative base with a NON-integer exponent (Python -> complex,
            # JS/Rust -> NaN). Roundabout to 0.0 in all faces, the same handler as sqrt/log of a
            # negative. Nested so each cond is a single comparison (no per-language "and"), reusing
            # the dialect's own floor() so it stays language-correct.
            floor_b = _sub(d.func1["floor"], a=vb)
            inner = _sub(_ternary(d), cond=f"{vb} != {floor_b}", t="0.0", f=expr)
            expr = _sub(_ternary(d), cond=f"{va} < 0.0", t=inner, f=expr)
        return expr, True
    if name in FUNC1:
        expr = _sub(d.func1[name], a=va)
        if safe and name == "sqrt":
            expr = _sub(_ternary(d), cond=f"{va} < 0.0", t="0.0", f=expr)
        elif safe and name == "log":  # log of a non-positive -> 0.0, the same chosen handler as sqrt
            expr = _sub(_ternary(d), cond=f"{va} <= 0.0", t="0.0", f=expr)
        return expr, False
    raise KeyError(f"op {name!r} not in v1 scalar core")


def emit(
    tokens: Sequence[int],
    lang: str,
    *,
    fn_name: str = "tongue_fn",
    arg_names: Sequence[str] | None = None,
    runnable: bool = False,
    safe: bool = False,
) -> str:
    """Emit a CA opcode program to a complete source string in `lang`."""
    if lang not in REGISTRY:
        raise ValueError(f"unknown language {lang!r}; have {sorted(REGISTRY)}")
    d = REGISTRY[lang]
    names = [BYTE_TO_NAME[t] for t in tokens]
    for n in names:
        if n not in PORTABLE_OPS:
            raise ValueError(f"op {n!r} (0x{NAME_TO_BYTE[n]:02x}) not in the portable op core for {lang}")
        if not _dialect_supports(d, n):  # portable, but this face hasn't implemented it yet
            raise ValueError(f"op {n!r} not implemented in the {lang!r} dialect (no func1/func2 template)")
    args = list(arg_names or ["a", "b", "c"])
    # identifiers only — a fn_name/arg like "f(0x05)" would inject a phantom (0xNN)
    # opcode tag into the source and break the face-decode bijection.
    if not (isinstance(fn_name, str) and fn_name.isidentifier()):
        raise ValueError(f"fn_name must be a valid identifier, got {fn_name!r}")
    if not all(isinstance(a, str) and a.isidentifier() for a in args):
        raise ValueError(f"arg_names must all be valid identifiers, got {args!r}")

    lines: List[str] = list(d.prelude)
    lines.append(_sub(d.fn_open, fn=fn_name, params=", ".join(args)))
    ind = d.indent
    lines.append(ind + _sub(d.stack_init, init=", ".join(args)))
    for n, tok in zip(names, tokens):
        expr, is_bin = _render(n, d, safe=safe)
        pop = d.pop2 if is_bin else d.pop1
        line = pop + _sub(d.push, expr=expr)
        lines.append(f"{ind}{line}  {d.comment} {n} (0x{tok:02x})")
    lines.append(ind + d.ret)
    lines.extend(d.fn_close)
    if runnable and d.main_tmpl:
        lines.append("")
        lines.extend(_sub(m, fn=fn_name) for m in d.main_tmpl)
    return "\n".join(lines) + "\n"


def program_bytes(*op_names: str) -> List[int]:
    return [NAME_TO_BYTE[n] for n in op_names]


# =========================================================================
# Reference dialects (the parallel tracks register here). 4 paradigms proven
# inline; the rest are added by the language-track workflow.
# =========================================================================
REGISTRY: Dict[str, Dialect] = {}


def register(d: Dialect) -> None:
    REGISTRY[d.name] = d


register(
    Dialect(
        name="python",
        ext="py",
        comment="#",
        indent="    ",
        prelude=("import math",),
        fn_open="def {fn}({params}):",
        stack_init="s = [{init}]",
        pop2="b = s.pop(); a = s.pop(); ",
        pop1="a = s.pop(); ",
        push="s.append({expr})",
        ret="return s[-1] if s else None",
        fn_close=(),
        func1={
            "neg": "-({a})",
            "abs": "abs({a})",
            "sqrt": "math.sqrt({a})",
            "floor": "math.floor({a})",
            "ceil": "math.ceil({a})",
            "round": "round({a})",
            "inc": "({a} + 1)",
            "dec": "({a} - 1)",
            "sign": "(1.0 if {a} > 0 else (-1.0 if {a} < 0 else 0.0))",
            "log": "math.log({a})",
            "exp": "math.exp({a})",
            "isnan": "(1.0 if math.isnan({a}) else 0.0)",
            "isinf": "(1.0 if math.isinf({a}) else 0.0)",
            "isfinite": "(1.0 if math.isfinite({a}) else 0.0)",
            "not": "float(~int({a}))",
        },
        func2={
            "pow": "({a} ** {b})",
            "min": "min({a}, {b})",
            "max": "max({a}, {b})",
            "mod": "({a} % {b})",
            "cmp": "(1.0 if {a} > {b} else (-1.0 if {a} < {b} else 0.0))",
            "and": "float(int({a}) & int({b}))",
            "or": "float(int({a}) | int({b}))",
            "xor": "float(int({a}) ^ int({b}))",
            "shl": "float(int({a}) << int({b}))",
            "shr": "float(int({a}) >> int({b}))",
        },
        cmp_tmpl="(1.0 if {cond} else 0.0)",
        main_tmpl=("if __name__ == '__main__':", "    print({fn}(2.0, 3.0, 4.0))"),
    )
)

register(
    Dialect(
        name="javascript",
        ext="js",
        comment="//",
        indent="  ",
        prelude=("function _round_ties_even(x) { const f = Math.floor(x); const d = x - f; if (d < 0.5) return f; if (d > 0.5) return f + 1; return (f % 2 === 0) ? f : f + 1; }",),
        fn_open="function {fn}({params}) {",
        stack_init="const s = [{init}];",
        pop2="{ const b = s.pop(); const a = s.pop(); ",
        pop1="{ const a = s.pop(); ",
        push="s.push({expr}); }",
        ret="return s.length ? s[s.length - 1] : null;",
        fn_close=("}",),
        func1={
            "neg": "-({a})",
            "abs": "Math.abs({a})",
            "sqrt": "Math.sqrt({a})",
            "floor": "Math.floor({a})",
            "ceil": "Math.ceil({a})",
            "round": "_round_ties_even({a})",
            "inc": "({a} + 1)",
            "dec": "({a} - 1)",
            "sign": "({a} > 0 ? 1.0 : ({a} < 0 ? -1.0 : 0.0))",
            "log": "Math.log({a})",
            "exp": "Math.exp({a})",
            "isnan": "(Number.isNaN({a}) ? 1.0 : 0.0)",
            "isinf": "((!Number.isFinite({a}) && !Number.isNaN({a})) ? 1.0 : 0.0)",
            "isfinite": "(Number.isFinite({a}) ? 1.0 : 0.0)",
            "not": "(~({a}))",
        },
        func2={
            "pow": "Math.pow({a}, {b})",
            "min": "Math.min({a}, {b})",
            "max": "Math.max({a}, {b})",
            "mod": "({a} - {b} * Math.floor({a} / {b}))",
            "cmp": "({a} > {b} ? 1.0 : ({a} < {b} ? -1.0 : 0.0))",
            "and": "(({a}) & ({b}))",
            "or": "(({a}) | ({b}))",
            "xor": "(({a}) ^ ({b}))",
            "shl": "(({a}) << ({b}))",
            "shr": "(({a}) >> ({b}))",
        },
        cmp_tmpl="({cond} ? 1.0 : 0.0)",
        main_tmpl=("console.log({fn}(2.0, 3.0, 4.0));",),
    )
)

register(
    Dialect(
        name="c",
        ext="c",
        comment="//",
        indent="    ",
        prelude=(
            "#include <stdio.h>",
            "#include <math.h>",
            "static double cmin(double a, double b){return a<b?a:b;}",
            "static double cmax(double a, double b){return a>b?a:b;}",
        ),
        fn_open="double {fn}(double a0, double b0, double c0) {",
        stack_init="double s[1024]; int sp = 0; s[sp++]=a0; s[sp++]=b0; s[sp++]=c0;",
        pop2="{ double b = s[--sp]; double a = s[--sp]; ",
        pop1="{ double a = s[--sp]; ",
        push="s[sp++] = {expr}; }",
        ret="return sp > 0 ? s[sp-1] : 0.0;",
        fn_close=("}",),
        func1={
            "neg": "-({a})",
            "abs": "fabs({a})",
            "sqrt": "sqrt({a})",
            "floor": "floor({a})",
            "ceil": "ceil({a})",
            "round": "round({a})",
            "inc": "({a} + 1)",
            "dec": "({a} - 1)",
            "sign": "(({a}) > 0 ? 1.0 : (({a}) < 0 ? -1.0 : 0.0))",
            "log": "log({a})",
            "exp": "exp({a})",
            "isnan": "(isnan({a}) ? 1.0 : 0.0)",
            "isinf": "(isinf({a}) ? 1.0 : 0.0)",
            "isfinite": "(isfinite({a}) ? 1.0 : 0.0)",
            "not": "(double)(~((long long)({a})))",
        },
        func2={
            "pow": "pow({a}, {b})",
            "min": "cmin({a}, {b})",
            "max": "cmax({a}, {b})",
            "mod": "fmod({a}, {b})",
            "cmp": "(({a}) > ({b}) ? 1.0 : (({a}) < ({b}) ? -1.0 : 0.0))",
            # 'long long' (>=64-bit on every platform, matching Rust i64) -- C 'long' is 32-bit on Windows
            "and": "(double)(((long long)({a})) & ((long long)({b})))",
            "or": "(double)(((long long)({a})) | ((long long)({b})))",
            "xor": "(double)(((long long)({a})) ^ ((long long)({b})))",
            "shl": "(double)(((long long)({a})) << ((long long)({b})))",
            "shr": "(double)(((long long)({a})) >> ((long long)({b})))",
        },
        cmp_tmpl="(({cond}) ? 1.0 : 0.0)",
        main_tmpl=("int main(void) {", '    printf("%.17g\\n", {fn}(2.0, 3.0, 4.0));', "    return 0;", "}"),
    )
)

register(
    Dialect(
        name="rust",
        ext="rs",
        comment="//",
        indent="    ",
        prelude=(),
        fn_open="fn {fn}(a0: f64, b0: f64, c0: f64) -> f64 {",
        stack_init="let mut s: Vec<f64> = vec![a0, b0, c0];",
        pop2="{ let b = s.pop().unwrap(); let a = s.pop().unwrap(); ",
        pop1="{ let a = s.pop().unwrap(); ",
        push="s.push({expr}); }",
        ret="*s.last().unwrap_or(&0.0)",
        fn_close=("}",),
        func1={
            "neg": "-({a})",
            "abs": "({a}).abs()",
            "sqrt": "({a}).sqrt()",
            "floor": "({a}).floor()",
            "ceil": "({a}).ceil()",
            "round": "({a}).round_ties_even()",
            "inc": "({a} + 1.0)",
            "dec": "({a} - 1.0)",
            "sign": "(if {a} > 0.0 { 1.0 } else if {a} < 0.0 { -1.0 } else { 0.0 })",
            "log": "({a}).ln()",
            "exp": "({a}).exp()",
            "isnan": "(if ({a}).is_nan() { 1.0 } else { 0.0 })",
            "isinf": "(if ({a}).is_infinite() { 1.0 } else { 0.0 })",
            "isfinite": "(if ({a}).is_finite() { 1.0 } else { 0.0 })",
            "not": "((!(({a}) as i64)) as f64)",
        },
        func2={
            "pow": "({a}).powf({b})",
            "min": "({a}).min({b})",
            "max": "({a}).max({b})",
            "mod": "({a} - {b} * ({a} / {b}).floor())",
            "cmp": "(if {a} > {b} { 1.0 } else if {a} < {b} { -1.0 } else { 0.0 })",
            "and": "(((({a}) as i64) & (({b}) as i64)) as f64)",
            "or": "(((({a}) as i64) | (({b}) as i64)) as f64)",
            "xor": "(((({a}) as i64) ^ (({b}) as i64)) as f64)",
            "shl": "(((({a}) as i64) << (({b}) as i64)) as f64)",
            "shr": "(((({a}) as i64) >> (({b}) as i64)) as f64)",
        },
        cmp_tmpl="(if {cond} { 1.0 } else { 0.0 })",
        main_tmpl=("fn main() {", '    println!("{}", {fn}(2.0, 3.0, 4.0));', "}"),
    )
)


def _load_bundled_dialects() -> None:
    """Register the workflow-authored language tracks (data, no per-opcode code)."""
    import json
    from pathlib import Path

    path = Path(__file__).with_name("polyglot_dialects.json")
    if not path.exists():
        return
    fields = set(Dialect.__dataclass_fields__)
    for raw in json.loads(path.read_text(encoding="utf-8")):
        kw = {k: v for k, v in raw.items() if k in fields}
        # JSON arrays -> tuples for the tuple-typed fields
        for tk in ("prelude", "fn_close", "main_tmpl"):
            if tk in kw:
                kw[tk] = tuple(kw[tk])
        try:
            register(Dialect(**kw))
        except TypeError:
            continue  # skip a malformed track rather than break the registry


_load_bundled_dialects()


def languages() -> List[str]:
    return sorted(REGISTRY)


def _demo() -> None:
    prog = program_bytes("add", "mul")  # (a+b)*... over stack [a,b,c]
    print(f"languages: {languages()}\n")
    for lang in languages():
        src = emit(prog, lang, runnable=True)
        print(f"=== {lang} ===")
        print(src)


if __name__ == "__main__":
    _demo()
