"""
Polyglot stack-machine emitter — one core, every language face.
====================================================================

The cube: the CENTER is the binary/trit core (bit_spine) + the CA 64-opcode
table (ca_opcode_table). Each FACE is a programming language. This module emits
a CA opcode program to compilable source in ANY registered language, so the
same core program "compiles no matter what."

Unlike tongue_isa (which bakes a field per language into every opcode), each
language here is a pure DATA `Dialect` — a registry entry. Adding a language is
one independent track: fill a Dialect literal, register it. Nothing else changes.

Emitted source is validated two ways:
  * real compile+run where the toolchain exists (python always; node/rust/...),
  * tree-sitter parse (rust/ast_cube_poly) for every language without a toolchain.

Op coverage (v1, the cleanly-portable scalar core over a float64 stack):
  arithmetic  add sub mul div mod neg inc dec
  math fns    pow abs sqrt floor ceil round min max
  comparison  eq neq lt lte gt gte   (-> 1.0 / 0.0, keeps the number stack)
The remaining CA ops (bitwise, aggregation) extend via each Dialect's prelude.
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
FUNC2 = {"pow", "min", "max", "mod"}  # pop a,b -> dialect.func2[name]
FUNC1 = {"neg", "abs", "sqrt", "floor", "ceil", "round", "inc", "dec"}  # pop a

SCALAR_OPS = set(BINOPS) | set(CMPS) | FUNC2 | FUNC1


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
    cmp_tmpl: str = "(1.0 if {cond} else 0.0)"  # ternary keeping number stack
    main_tmpl: Tuple[str, ...] = ()  # optional runnable main(); {fn} placeholder
    expr_a: str = "a"  # expression spelling for the local a binding (PHP uses $a)
    expr_b: str = "b"  # expression spelling for the local b binding


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
    """Return (push-expression using temp vars a/b, is_binary)."""
    a = d.expr_a
    b = d.expr_b
    if name in BINOPS:
        op = d.binop_over.get(name, BINOPS[name])
        expr = f"{a} {op} {b}"
        if safe and name == "div":
            expr = _sub(_ternary(d), cond=f"{b} == 0.0", t="0.0", f=f"{a} / {b}")
        return expr, True
    if name in CMPS:
        op = CMPS[name]
        return _sub(d.cmp_tmpl, cond=f"{a} {op} {b}"), True
    if name in FUNC2:
        expr = _sub(d.func2[name], a=a, b=b)
        if safe and name == "mod":
            expr = _sub(_ternary(d), cond=f"{b} == 0.0", t="0.0", f=expr)
        return expr, True
    if name in FUNC1:
        expr = _sub(d.func1[name], a=a)
        if safe and name == "sqrt":
            expr = _sub(_ternary(d), cond=f"{a} < 0.0", t="0.0", f=expr)
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
        if n not in SCALAR_OPS:
            raise ValueError(f"op {n!r} (0x{NAME_TO_BYTE[n]:02x}) not in v1 scalar core for {lang}")
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
        },
        func2={"pow": "({a} ** {b})", "min": "min({a}, {b})", "max": "max({a}, {b})", "mod": "({a} % {b})"},
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
        prelude=(),
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
            "round": "Math.round({a})",
            "inc": "({a} + 1)",
            "dec": "({a} - 1)",
        },
        func2={
            "pow": "Math.pow({a}, {b})",
            "min": "Math.min({a}, {b})",
            "max": "Math.max({a}, {b})",
            "mod": "({a} % {b})",
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
        },
        func2={"pow": "pow({a}, {b})", "min": "cmin({a}, {b})", "max": "cmax({a}, {b})", "mod": "fmod({a}, {b})"},
        cmp_tmpl="(({cond}) ? 1.0 : 0.0)",
        main_tmpl=("int main(void) {", '    printf("%g\\n", {fn}(2.0, 3.0, 4.0));', "    return 0;", "}"),
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
            "round": "({a}).round()",
            "inc": "({a} + 1.0)",
            "dec": "({a} - 1.0)",
        },
        func2={"pow": "({a}).powf({b})", "min": "({a}).min({b})", "max": "({a}).max({b})", "mod": "({a} % {b})"},
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
