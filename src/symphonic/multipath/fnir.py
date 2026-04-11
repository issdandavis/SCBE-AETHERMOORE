"""FnIR — canonical Function-call Intermediate Representation.

Stage 1 of the Prism->Rainbow->Beam multipath encoder. Source code in any
of the six tongue-languages lowers to FnIR; FnIR is the white light that
the per-tongue binary tables (Stage 2) split into the rainbow.

Op vocabulary is fixed at exactly 64 primitives (6-bit op_id) so every
tongue's binary table can index it directly. Categories are stable; new
languages add tokens, never new ops.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import IntEnum, IntFlag
from typing import Any, List, Optional


# --- Effects bitfield ----------------------------------------------------
class Effect(IntFlag):
    NONE       = 0
    MEM_READ   = 1 << 0
    MEM_WRITE  = 1 << 1
    IO         = 1 << 2
    ALLOC      = 1 << 3
    FREE       = 1 << 4
    SPAWN      = 1 << 5
    BLOCK      = 1 << 6   # may suspend / await
    RAISE      = 1 << 7   # may throw
    NONDET     = 1 << 8   # nondeterministic


# --- Operation vocabulary (exactly 64) -----------------------------------
class Op(IntEnum):
    # Bind & assign (5)
    ASSIGN = 0; DECLARE = 1; DESTRUCT = 2; UNPACK = 3; BIND = 4
    # Arithmetic (10)
    ADD = 5; SUB = 6; MUL = 7; DIV = 8; MOD = 9
    POW = 10; NEG = 11; ABS = 12; FLOOR = 13; CEIL = 14
    # Compare & logic (9)
    EQ = 15; NEQ = 16; LT = 17; GT = 18; LE = 19; GE = 20
    AND = 21; OR = 22; NOT = 23
    # Control flow (10)
    BRANCH = 24; LOOP_WHILE = 25; FOR_EACH = 26; BREAK = 27; CONTINUE = 28
    RETURN = 29; RAISE = 30; MATCH = 31; TRY_CATCH = 32; YIELD = 33
    # Function & call (5)
    CALL = 34; CLOSURE = 35; APPLY = 36; RECURSE = 37; TAILCALL = 38
    # Memory & access (8)
    ALLOC = 39; FREE = 40; READ = 41; WRITE = 42
    INDEX_GET = 43; INDEX_SET = 44; FIELD_GET = 45; FIELD_SET = 46
    # Collections (8)
    MAP = 47; FOLD = 48; FILTER = 49; ZIP = 50
    CONCAT = 51; LENGTH = 52; SLICE = 53; PUSH = 54
    # Concurrency (6)
    SPAWN = 55; SEND = 56; RECV = 57; AWAIT = 58; LOCK = 59; ATOMIC = 60
    # Type & meta (3)
    CAST = 61; TYPE_CHECK = 62; DISPATCH = 63


assert len(Op) == 64, f"Op vocabulary must be exactly 64, got {len(Op)}"


# --- Op metadata: arity hint, purity, effects ---------------------------
@dataclass(frozen=True)
class OpMeta:
    arity: int          # -1 = variadic
    pure: bool
    effects: Effect


_E = Effect
OP_META: dict[Op, OpMeta] = {
    Op.ASSIGN:     OpMeta( 2, False, _E.MEM_WRITE),
    Op.DECLARE:    OpMeta( 2, False, _E.ALLOC | _E.MEM_WRITE),
    Op.DESTRUCT:   OpMeta( 1, False, _E.FREE),
    Op.UNPACK:     OpMeta(-1, True,  _E.NONE),
    Op.BIND:       OpMeta( 2, False, _E.MEM_WRITE),

    Op.ADD: OpMeta(2, True, _E.NONE), Op.SUB: OpMeta(2, True, _E.NONE),
    Op.MUL: OpMeta(2, True, _E.NONE), Op.DIV: OpMeta(2, True, _E.RAISE),
    Op.MOD: OpMeta(2, True, _E.RAISE), Op.POW: OpMeta(2, True, _E.NONE),
    Op.NEG: OpMeta(1, True, _E.NONE), Op.ABS: OpMeta(1, True, _E.NONE),
    Op.FLOOR: OpMeta(1, True, _E.NONE), Op.CEIL: OpMeta(1, True, _E.NONE),

    Op.EQ: OpMeta(2, True, _E.NONE), Op.NEQ: OpMeta(2, True, _E.NONE),
    Op.LT: OpMeta(2, True, _E.NONE), Op.GT: OpMeta(2, True, _E.NONE),
    Op.LE: OpMeta(2, True, _E.NONE), Op.GE: OpMeta(2, True, _E.NONE),
    Op.AND: OpMeta(2, True, _E.NONE), Op.OR: OpMeta(2, True, _E.NONE),
    Op.NOT: OpMeta(1, True, _E.NONE),

    Op.BRANCH:     OpMeta(-1, False, _E.NONDET),
    Op.LOOP_WHILE: OpMeta( 2, False, _E.NONDET | _E.BLOCK),
    Op.FOR_EACH:   OpMeta( 2, False, _E.MEM_READ),
    Op.BREAK:      OpMeta( 0, False, _E.NONE),
    Op.CONTINUE:   OpMeta( 0, False, _E.NONE),
    Op.RETURN:     OpMeta( 1, False, _E.NONE),
    Op.RAISE:      OpMeta( 1, False, _E.RAISE),
    Op.MATCH:      OpMeta(-1, False, _E.NONDET),
    Op.TRY_CATCH:  OpMeta(-1, False, _E.RAISE),
    Op.YIELD:      OpMeta( 1, False, _E.BLOCK),

    Op.CALL:     OpMeta(-1, False, _E.IO | _E.MEM_READ | _E.MEM_WRITE),
    Op.CLOSURE:  OpMeta(-1, True,  _E.ALLOC),
    Op.APPLY:    OpMeta(-1, False, _E.IO),
    Op.RECURSE:  OpMeta(-1, False, _E.NONE),
    Op.TAILCALL: OpMeta(-1, False, _E.NONE),

    Op.ALLOC:     OpMeta( 1, False, _E.ALLOC),
    Op.FREE:      OpMeta( 1, False, _E.FREE),
    Op.READ:      OpMeta( 1, True,  _E.MEM_READ),
    Op.WRITE:     OpMeta( 2, False, _E.MEM_WRITE),
    Op.INDEX_GET: OpMeta( 2, True,  _E.MEM_READ),
    Op.INDEX_SET: OpMeta( 3, False, _E.MEM_WRITE),
    Op.FIELD_GET: OpMeta( 2, True,  _E.MEM_READ),
    Op.FIELD_SET: OpMeta( 3, False, _E.MEM_WRITE),

    Op.MAP:    OpMeta(2, True,  _E.NONE),
    Op.FOLD:   OpMeta(3, True,  _E.NONE),
    Op.FILTER: OpMeta(2, True,  _E.NONE),
    Op.ZIP:    OpMeta(2, True,  _E.NONE),
    Op.CONCAT: OpMeta(2, True,  _E.NONE),
    Op.LENGTH: OpMeta(1, True,  _E.NONE),
    Op.SLICE:  OpMeta(3, True,  _E.NONE),
    Op.PUSH:   OpMeta(2, False, _E.MEM_WRITE),

    Op.SPAWN:  OpMeta(-1, False, _E.SPAWN),
    Op.SEND:   OpMeta( 2, False, _E.IO | _E.BLOCK),
    Op.RECV:   OpMeta( 1, False, _E.IO | _E.BLOCK),
    Op.AWAIT:  OpMeta( 1, False, _E.BLOCK),
    Op.LOCK:   OpMeta( 1, False, _E.BLOCK),
    Op.ATOMIC: OpMeta(-1, False, _E.MEM_WRITE),

    Op.CAST:       OpMeta(2, True,  _E.RAISE),
    Op.TYPE_CHECK: OpMeta(2, True,  _E.NONE),
    Op.DISPATCH:   OpMeta(-1, False, _E.IO),
}

assert len(OP_META) == 64, "OP_META must cover every Op"


# --- FnIR node -----------------------------------------------------------
@dataclass
class FnIR:
    op: Op
    args: List[Any] = field(default_factory=list)   # FnIR | literal | str
    children: List["FnIR"] = field(default_factory=list)
    name: Optional[str] = None

    @property
    def meta(self) -> OpMeta:
        return OP_META[self.op]

    @property
    def effects(self) -> Effect:
        e = self.meta.effects
        for c in self.children:
            e |= c.effects
        return e

    @property
    def pure(self) -> bool:
        return self.effects == Effect.NONE

    def to_dict(self) -> dict:
        return {
            "op": self.op.name,
            "name": self.name,
            "args": [a.to_dict() if isinstance(a, FnIR) else a for a in self.args],
            "children": [c.to_dict() for c in self.children],
        }


# --- Python AST -> FnIR --------------------------------------------------
_BINOP = {
    ast.Add: Op.ADD, ast.Sub: Op.SUB, ast.Mult: Op.MUL,
    ast.Div: Op.DIV, ast.Mod: Op.MOD, ast.Pow: Op.POW,
    ast.FloorDiv: Op.FLOOR,
}
_CMPOP = {
    ast.Eq: Op.EQ, ast.NotEq: Op.NEQ,
    ast.Lt: Op.LT, ast.Gt: Op.GT,
    ast.LtE: Op.LE, ast.GtE: Op.GE,
}
_BOOLOP = {ast.And: Op.AND, ast.Or: Op.OR}
_UNARYOP = {ast.USub: Op.NEG, ast.Not: Op.NOT}


class PythonToFnIR(ast.NodeVisitor):
    """Lower a Python ast.AST node into an FnIR tree."""

    def lower(self, src: str) -> FnIR:
        tree = ast.parse(src)
        return self.visit(tree)

    # --- module / function -------------------------------------------
    def visit_Module(self, node: ast.Module) -> FnIR:
        return FnIR(Op.CLOSURE, name="<module>",
                    children=[self.visit(s) for s in node.body])

    def visit_FunctionDef(self, node: ast.FunctionDef) -> FnIR:
        return FnIR(Op.CLOSURE, name=node.name,
                    args=[a.arg for a in node.args.args],
                    children=[self.visit(s) for s in node.body])

    # --- statements --------------------------------------------------
    def visit_Assign(self, node: ast.Assign) -> FnIR:
        target = node.targets[0]
        name = target.id if isinstance(target, ast.Name) else ast.dump(target)
        return FnIR(Op.ASSIGN, name=name, children=[self.visit(node.value)])

    def visit_AugAssign(self, node: ast.AugAssign) -> FnIR:
        op = _BINOP.get(type(node.op), Op.ADD)
        return FnIR(Op.ASSIGN,
                    name=getattr(node.target, "id", "?"),
                    children=[FnIR(op, children=[self.visit(node.target),
                                                 self.visit(node.value)])])

    def visit_Return(self, node: ast.Return) -> FnIR:
        return FnIR(Op.RETURN,
                    children=[self.visit(node.value)] if node.value else [])

    def visit_If(self, node: ast.If) -> FnIR:
        return FnIR(Op.BRANCH,
                    children=[self.visit(node.test),
                              FnIR(Op.CLOSURE, name="<then>",
                                   children=[self.visit(s) for s in node.body]),
                              FnIR(Op.CLOSURE, name="<else>",
                                   children=[self.visit(s) for s in node.orelse])])

    def visit_While(self, node: ast.While) -> FnIR:
        return FnIR(Op.LOOP_WHILE,
                    children=[self.visit(node.test),
                              FnIR(Op.CLOSURE, name="<body>",
                                   children=[self.visit(s) for s in node.body])])

    def visit_For(self, node: ast.For) -> FnIR:
        return FnIR(Op.FOR_EACH,
                    name=getattr(node.target, "id", "?"),
                    children=[self.visit(node.iter),
                              FnIR(Op.CLOSURE, name="<body>",
                                   children=[self.visit(s) for s in node.body])])

    def visit_Raise(self, node: ast.Raise) -> FnIR:
        return FnIR(Op.RAISE,
                    children=[self.visit(node.exc)] if node.exc else [])

    def visit_Try(self, node: ast.Try) -> FnIR:
        kids = [FnIR(Op.CLOSURE, name="<try>",
                     children=[self.visit(s) for s in node.body])]
        for h in node.handlers:
            kids.append(FnIR(Op.CLOSURE, name="<except>",
                             children=[self.visit(s) for s in h.body]))
        return FnIR(Op.TRY_CATCH, children=kids)

    def visit_Expr(self, node: ast.Expr) -> FnIR:
        return self.visit(node.value)

    # --- expressions -------------------------------------------------
    def visit_BinOp(self, node: ast.BinOp) -> FnIR:
        op = _BINOP.get(type(node.op), Op.ADD)
        return FnIR(op, children=[self.visit(node.left), self.visit(node.right)])

    def visit_UnaryOp(self, node: ast.UnaryOp) -> FnIR:
        op = _UNARYOP.get(type(node.op), Op.NEG)
        return FnIR(op, children=[self.visit(node.operand)])

    def visit_BoolOp(self, node: ast.BoolOp) -> FnIR:
        op = _BOOLOP.get(type(node.op), Op.AND)
        return FnIR(op, children=[self.visit(v) for v in node.values])

    def visit_Compare(self, node: ast.Compare) -> FnIR:
        op = _CMPOP.get(type(node.ops[0]), Op.EQ)
        return FnIR(op, children=[self.visit(node.left),
                                  self.visit(node.comparators[0])])

    def visit_Call(self, node: ast.Call) -> FnIR:
        name = getattr(node.func, "id", None) or ast.dump(node.func)
        return FnIR(Op.CALL, name=name,
                    children=[self.visit(a) for a in node.args])

    def visit_Subscript(self, node: ast.Subscript) -> FnIR:
        return FnIR(Op.INDEX_GET,
                    children=[self.visit(node.value), self.visit(node.slice)])

    def visit_Attribute(self, node: ast.Attribute) -> FnIR:
        return FnIR(Op.FIELD_GET, name=node.attr,
                    children=[self.visit(node.value)])

    def visit_Name(self, node: ast.Name) -> FnIR:
        return FnIR(Op.READ, name=node.id)

    def visit_Constant(self, node: ast.Constant) -> FnIR:
        return FnIR(Op.READ, name=repr(node.value))

    def visit_List(self, node: ast.List) -> FnIR:
        return FnIR(Op.ALLOC, name="list",
                    children=[self.visit(e) for e in node.elts])

    def visit_Tuple(self, node: ast.Tuple) -> FnIR:
        return FnIR(Op.ALLOC, name="tuple",
                    children=[self.visit(e) for e in node.elts])

    def visit_Dict(self, node: ast.Dict) -> FnIR:
        return FnIR(Op.ALLOC, name="dict",
                    children=[self.visit(v) for v in node.values if v])

    def generic_visit(self, node):
        return FnIR(Op.READ, name=type(node).__name__)


def lower_python(src: str) -> FnIR:
    return PythonToFnIR().lower(src)


# --- Cross-tongue surface examples ---------------------------------------
# Per-op surface forms in each of the six target languages. Used by Stage 3
# trit-table generators and by docs to ground "this op looks like X in
# tongue Y". Coverage is partial — only entries that are actually correct
# in all six tongues live here. Add more by appending; never silently mutate.
TONGUE_LANGS: tuple[str, ...] = ("KO", "AV", "RU", "CA", "UM", "DR")

OP_EXAMPLES: dict[Op, dict[str, str]] = {
    Op.ADD: {
        "KO": "a + b",
        "AV": "a + b",
        "RU": "a + b",
        "CA": "a + b",
        "UM": "a + b",
        "DR": "(+) a b",
    },
    Op.SUB: {
        "KO": "a - b", "AV": "a - b", "RU": "a - b",
        "CA": "a - b", "UM": "a - b", "DR": "(-) a b",
    },
    Op.MUL: {
        "KO": "a * b", "AV": "a * b", "RU": "a * b",
        "CA": "a * b", "UM": "a * b", "DR": "(*) a b",
    },
    Op.DIV: {
        "KO": "a / b", "AV": "a / b", "RU": "a / b",
        "CA": "a / b", "UM": "a / b", "DR": "div a b",
    },
    Op.ASSIGN: {
        "KO": "x = v",
        "AV": "let x = v",
        "RU": "let x = v;",
        "CA": "x = v;",
        "UM": "x = v",
        "DR": "let x = v in ...",
    },
    Op.DECLARE: {
        "KO": "x: T = v",
        "AV": "let x: T = v",
        "RU": "let x: T = v;",
        "CA": "T x = v;",
        "UM": "x::T = v",
        "DR": "x :: T; x = v",
    },
    Op.BRANCH: {
        "KO": "if c: ... else: ...",
        "AV": "if (c) { ... } else { ... }",
        "RU": "if c { ... } else { ... }",
        "CA": "if (c) { ... } else { ... }",
        "UM": "if c ... else ... end",
        "DR": "if c then ... else ...",
    },
    Op.LOOP_WHILE: {
        "KO": "while c: ...",
        "AV": "while (c) { ... }",
        "RU": "while c { ... }",
        "CA": "while (c) { ... }",
        "UM": "while c ... end",
        "DR": "let loop = if c then ... >> loop else pure ()",
    },
    Op.RETURN: {
        "KO": "return v",
        "AV": "return v;",
        "RU": "return v;",
        "CA": "return v;",
        "UM": "return v",
        "DR": "pure v",
    },
    Op.CALL: {
        "KO": "f(x, y)",
        "AV": "f(x, y)",
        "RU": "f(x, y)",
        "CA": "f(x, y);",
        "UM": "f(x, y)",
        "DR": "f x y",
    },
    Op.READ: {
        "KO": "x", "AV": "x", "RU": "x",
        "CA": "x", "UM": "x", "DR": "x",
    },
    Op.WRITE: {
        "KO": "x = v",
        "AV": "x = v;",
        "RU": "*x = v;",
        "CA": "*x = v;",
        "UM": "x[] = v",
        "DR": "writeIORef x v",
    },
    Op.MAP: {
        "KO": "[f(e) for e in xs]",
        "AV": "xs.map(f)",
        "RU": "xs.iter().map(f).collect()",
        "CA": "for(i=0;i<n;i++) ys[i]=f(xs[i]);",
        "UM": "map(f, xs)",
        "DR": "map f xs",
    },
    Op.FOLD: {
        "KO": "reduce(f, xs, init)",
        "AV": "xs.reduce(f, init)",
        "RU": "xs.iter().fold(init, f)",
        "CA": "for(i=0;i<n;i++) acc=f(acc,xs[i]);",
        "UM": "foldl(f, init, xs)",
        "DR": "foldl f init xs",
    },
    Op.SPAWN: {
        "KO": "threading.Thread(target=f).start()",
        "AV": "new Worker(f)",
        "RU": "std::thread::spawn(f)",
        "CA": "pthread_create(&t, NULL, f, NULL);",
        "UM": "Threads.@spawn f()",
        "DR": "forkIO (f)",
    },
}


def example(op: Op, tongue: str) -> str | None:
    """Look up the surface form for `op` in `tongue`. None if not catalogued."""
    return OP_EXAMPLES.get(op, {}).get(tongue)


def example_row(op: Op) -> dict[str, str]:
    """All catalogued tongue forms for an op (empty dict if uncatalogued)."""
    return dict(OP_EXAMPLES.get(op, {}))


# --- Actionable: render an FnIR tree into a target tongue ----------------
# This is the part that does work. Walks an FnIR node and emits a string
# in the requested tongue using OP_EXAMPLES as the surface-form template.
# Not a full code generator — a structural renderer that proves the
# multipath spine actually round-trips: source -> FnIR -> tongue surface.

_BIN_OPS = {Op.ADD, Op.SUB, Op.MUL, Op.DIV, Op.MOD, Op.POW,
            Op.EQ, Op.NEQ, Op.LT, Op.GT, Op.LE, Op.GE, Op.AND, Op.OR}
_BIN_SYM = {
    Op.ADD: "+", Op.SUB: "-", Op.MUL: "*", Op.DIV: "/", Op.MOD: "%",
    Op.POW: "**", Op.EQ: "==", Op.NEQ: "!=", Op.LT: "<", Op.GT: ">",
    Op.LE: "<=", Op.GE: ">=", Op.AND: "&&", Op.OR: "||",
}


def render(node: "FnIR", tongue: str = "KO", indent: int = 0) -> str:
    """Render an FnIR tree as source in `tongue`. Structural, not pretty."""
    if tongue not in TONGUE_LANGS:
        raise ValueError(f"unknown tongue: {tongue}")
    pad = "  " * indent
    op = node.op

    if op == Op.READ:
        return node.name or "_"

    if op in _BIN_OPS:
        sym = _BIN_SYM[op]
        if len(node.children) == 2:
            l = render(node.children[0], tongue, 0)
            r = render(node.children[1], tongue, 0)
            if tongue == "DR":
                return f"({sym}) ({l}) ({r})"
            return f"({l} {sym} {r})"

    if op == Op.NEG:
        inner = render(node.children[0], tongue, 0) if node.children else "_"
        return f"(-{inner})"

    if op == Op.NOT:
        inner = render(node.children[0], tongue, 0) if node.children else "_"
        return f"(!{inner})" if tongue != "DR" else f"(not {inner})"

    if op == Op.ASSIGN:
        val = render(node.children[0], tongue, 0) if node.children else "_"
        name = node.name or "_"
        if tongue in ("KO", "UM"):
            return f"{pad}{name} = {val}"
        if tongue in ("AV", "RU"):
            return f"{pad}let {name} = {val};"
        if tongue == "CA":
            return f"{pad}{name} = {val};"
        if tongue == "DR":
            return f"{pad}let {name} = {val}"

    if op == Op.RETURN:
        val = render(node.children[0], tongue, 0) if node.children else ""
        if tongue == "KO":
            return f"{pad}return {val}"
        if tongue == "DR":
            return f"{pad}pure {val}"
        return f"{pad}return {val};"

    if op == Op.BRANCH:
        cond = render(node.children[0], tongue, 0)
        then_body = _render_block(node.children[1], tongue, indent + 1) if len(node.children) > 1 else ""
        else_body = _render_block(node.children[2], tongue, indent + 1) if len(node.children) > 2 else ""
        if tongue == "KO":
            out = f"{pad}if {cond}:\n{then_body}"
            if else_body.strip():
                out += f"\n{pad}else:\n{else_body}"
            return out
        if tongue == "DR":
            return f"{pad}if {cond} then\n{then_body}\n{pad}else\n{else_body}"
        out = f"{pad}if ({cond}) {{\n{then_body}\n{pad}}}"
        if else_body.strip():
            out += f" else {{\n{else_body}\n{pad}}}"
        return out

    if op == Op.LOOP_WHILE:
        cond = render(node.children[0], tongue, 0)
        body = _render_block(node.children[1], tongue, indent + 1) if len(node.children) > 1 else ""
        if tongue == "KO":
            return f"{pad}while {cond}:\n{body}"
        if tongue == "UM":
            return f"{pad}while {cond}\n{body}\n{pad}end"
        if tongue == "DR":
            return f"{pad}-- while loop\n{pad}let go = if {cond} then\n{body}\n{pad}  >> go else pure ()"
        return f"{pad}while ({cond}) {{\n{body}\n{pad}}}"

    if op == Op.CALL:
        name = node.name or "f"
        args = [render(c, tongue, 0) for c in node.children]
        if tongue == "DR":
            return f"({name} {' '.join(args)})" if args else name
        return f"{name}({', '.join(args)})"

    if op == Op.CLOSURE:
        body = "\n".join(render(c, tongue, indent + 1) for c in node.children)
        name = node.name or "<anon>"
        if name in ("<then>", "<else>", "<body>", "<try>", "<except>"):
            return body
        if name == "<module>":
            return body
        params = ", ".join(str(a) for a in node.args)
        if tongue == "KO":
            return f"{pad}def {name}({params}):\n{body}"
        if tongue == "AV":
            return f"{pad}function {name}({params}) {{\n{body}\n{pad}}}"
        if tongue == "RU":
            return f"{pad}fn {name}({params}) {{\n{body}\n{pad}}}"
        if tongue == "CA":
            return f"{pad}void {name}({params}) {{\n{body}\n{pad}}}"
        if tongue == "UM":
            return f"{pad}function {name}({params})\n{body}\n{pad}end"
        if tongue == "DR":
            return f"{pad}{name} {params} =\n{body}"

    # Fallback: show the op + children inline
    kids = ", ".join(render(c, tongue, 0) for c in node.children)
    return f"{pad}{op.name.lower()}({kids})"


def _render_block(node: "FnIR", tongue: str, indent: int) -> str:
    if node.op == Op.CLOSURE:
        return "\n".join(render(c, tongue, indent) for c in node.children)
    return render(node, tongue, indent)


def transpile(src: str, tongue: str = "KO") -> str:
    """End-to-end: Python source -> FnIR -> target tongue surface."""
    return render(lower_python(src), tongue)


if __name__ == "__main__":
    import json
    sample = """
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)
"""
    ir = lower_python(sample)
    print(json.dumps(ir.to_dict(), indent=2))
    print(f"\nvocab size: {len(Op)}  meta entries: {len(OP_META)}")
