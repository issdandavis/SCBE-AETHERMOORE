"""opcode_compose.py -- write a NORMAL expression, get a VERIFIED opcode program.

This is the "how to code in opcode, applied to our system" bridge. Our CA core
(scbe.tongue_isa.compile_ca_tokens) is a STACK MACHINE in the Forth/JVM/WASM lineage
(von Thun: juxtaposition = function composition; Hamblin 1957: postfix consumes operands off a
pushdown stack). BUT it has a sharp constraint, verified empirically: it pushes ALL args first
then applies ops (no literal-push, no dup/swap, no branch). So it natively runs only the
RIGHT-COMB class -- op_k(a0, op_{k-1}(a1, ... op_1(a_{k-1}, a_k))) -- where every operator's
left input is a fresh argument and its right input is the running result.

This module closes the gap so a non-coder never has to hand-order a stack:
  infix expression  ->  AST  ->  (a) canonical postfix opcode stream (the Forth-style "code in
  opcode" you'd write by hand), and (b) EXECUTION on the real CA core, two ways that must agree:
    - node-by-node: each AST node = one verified opcode call on the core (always works; this is
      the LMC/accumulator trick -- park each intermediate, like a named cell);
    - native single program: if the tree is a right-comb (after commutative reordering), pack it
      into ONE compile_ca_tokens program -- real multi-op opcode coding.
  Then cross-check BOTH against an INDEPENDENT pure-Python oracle (not scbe).

FIREWALL: the postfix stream is the canonical teaching form; our core can't run a general
interleaved stream (no literal-push) so it executes per-node or as a right-comb pack -- stated,
not hidden. "Verified" here = executes on the real opcode core AND agrees with an independent
Python computation. Agreement is EVIDENCE, not a proof of correctness (the honest framing).
Grounded in: Forth (Moore), Joy (von Thun 2002), JVM spec (Lindholm/Yellin), WebAssembly
(Haas et al. PLDI 2017), the Dragon Book (Aho et al. 2006, postorder lowering), LMC (Madnick 1965).
"""
from __future__ import annotations
import math
import sys
from functools import lru_cache

# WHERE scbe LIVES. This used to be one hardcoded path -- a git WORKTREE
# (C:\Users\issda\instrument-wt\python) that has since been removed, so every import of this module
# died with "No module named 'scbe'" and took the whole voice loop down with it.
# A worktree is a temporary thing. Never pin an import to one. Search the real checkouts instead,
# and say which paths were tried when none of them work.
import os

_SCBE_CANDIDATES = [
    os.environ.get("SCBE_PYTHON", ""),
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "SCBE-AETHERMOORE",
        "python",
    ),
    r"C:\Users\ddavi\dev\SCBE-AETHERMOORE\python",
    r"C:\dev\.repos_clone\SCBE-AETHERMOORE\python",
    r"C:\dev\SCBE-AETHERMOORE\python",
    r"C:\Users\issda\instrument-wt\python",
]
for _p in _SCBE_CANDIDATES:
    if os.path.exists(os.path.join(_p, "scbe", "instrument.py")):
        if _p not in sys.path:
            sys.path.insert(0, _p)
        break
else:
    raise ImportError(
        "scbe.instrument not found. Looked in:\n  " + "\n  ".join(_SCBE_CANDIDATES) +
        "\nSet SCBE_PYTHON or add the checkout that holds python/scbe/instrument.py."
    )
from scbe.instrument import _NAME_TO_BYTE, ca_word_for_opcode          # noqa: E402
from scbe.tongue_isa import compile_ca_tokens, runtime_prelude          # noqa: E402

# infix operators -> CA op name
BINOP = {"+": "add", "-": "sub", "*": "mul", "/": "div", "%": "mod"}
# ops whose operands may be reordered (lets the right-comb packer push a leaf to the left)
COMMUTATIVE = {"add", "mul", "min", "max", "and", "or", "xor", "eq", "neq", "nand", "nor"}

# INDEPENDENT oracle (pure Python, NOT scbe) for cross-checking the core's result
ORACLE = {
    "add": lambda a, b: a + b, "sub": lambda a, b: a - b, "mul": lambda a, b: a * b,
    "div": lambda a, b: a / b if b else 0.0, "mod": lambda a, b: math.fmod(a, b) if b else 0.0,
    "pow": lambda a, b: a ** b, "neg": lambda a: -a, "abs": lambda a: abs(a),
    "sqrt": lambda a: math.sqrt(a) if a >= 0 else 0.0,
    "min": lambda a, b: min(a, b), "max": lambda a, b: max(a, b),
    "clamp": lambda a, b, c: min(max(a, b), c),
    "within": lambda a, b, c: 1.0 if min(b, c) <= a <= max(b, c) else 0.0,
}


# ---- tokenizer + recursive-descent parser: infix -> AST ----
def tokenize(s: str):
    toks, i = [], 0
    while i < len(s):
        c = s[i]
        if c.isspace():
            i += 1
        elif c in "+-*/%(),":
            toks.append(c); i += 1
        elif c.isdigit() or c == ".":
            j = i
            while j < len(s) and (s[j].isdigit() or s[j] == "."):
                j += 1
            toks.append(("num", float(s[i:j]))); i = j
        elif c.isalpha() or c == "_":
            j = i
            while j < len(s) and (s[j].isalnum() or s[j] == "_"):
                j += 1
            toks.append(("name", s[i:j])); i = j
        else:
            raise ValueError(f"bad character {c!r} in expression")
    return toks


class _P:
    def __init__(self, toks): self.t, self.i = toks, 0
    def peek(self): return self.t[self.i] if self.i < len(self.t) else None
    def take(self): tok = self.t[self.i]; self.i += 1; return tok

    def expr(self):                       # + and - (lowest precedence)
        node = self.term()
        while self.peek() in ("+", "-"):
            op = self.take(); node = ("op", BINOP[op], [node, self.term()])
        return node

    def term(self):                       # * / %
        node = self.factor()
        while self.peek() in ("*", "/", "%"):
            op = self.take(); node = ("op", BINOP[op], [node, self.factor()])
        return node

    def factor(self):
        tok = self.peek()
        if tok == "-":                     # unary minus
            self.take(); return ("op", "neg", [self.factor()])
        if tok == "(":
            self.take(); node = self.expr()
            if self.take() != ")":
                raise ValueError("missing )")
            return node
        if isinstance(tok, tuple) and tok[0] == "num":
            self.take(); return ("num", tok[1])
        if isinstance(tok, tuple) and tok[0] == "name":
            self.take()
            if self.peek() == "(":         # function call: name(args...)
                self.take(); args = [self.expr()]
                while self.peek() == ",":
                    self.take(); args.append(self.expr())
                if self.take() != ")":
                    raise ValueError("missing ) in call")
                return ("op", tok[1], args)
            return ("var", tok[1])         # bare name = variable
        raise ValueError(f"unexpected token {tok!r}")


def parse(s): return _P(tokenize(s)).expr()


# ---- postfix (the canonical "code in opcode" form) ----
def to_rpn(node):
    if node[0] in ("num", "var"):
        return [node[1] if node[0] == "num" else node[1]]
    out = []
    for ch in node[2]:
        out += to_rpn(ch)
    out.append(node[1])                    # operator after its operands (post-order)
    return out


# ---- execution on the real CA opcode core ----
@lru_cache(maxsize=256)
def _compiled_core(opcodes: tuple[int, ...], arity: int):
    """Compile one bounded opcode shape once; runtime argument values stay dynamic."""

    names = [f"a{i}" for i in range(arity)]
    prog = compile_ca_tokens(list(opcodes), target="python", fn_name="ca", arg_names=names)
    src = runtime_prelude("python") + "\n\ndef ca(" + ", ".join(names) + "):\n"
    src += "\n".join("    " + ln for ln in prog.body_lines)
    ns: dict = {}
    exec(src, ns)  # noqa: S102 - emitted by the deterministic compiler
    return ns["ca"]


def run_core(opcodes, args):
    function = _compiled_core(tuple(int(opcode) for opcode in opcodes), len(args))
    return float(function(*args))


def eval_core(node, vars):
    """Post-order: each op node = ONE verified opcode call on the real core (named-cell style)."""
    if node[0] == "num":
        return node[1]
    if node[0] == "var":
        return float(vars[node[1]])
    vals = [eval_core(ch, vars) for ch in node[2]]
    return run_core([_NAME_TO_BYTE[node[1]]], vals)


def eval_oracle(node, vars):
    if node[0] == "num":
        return node[1]
    if node[0] == "var":
        return float(vars[node[1]])
    vals = [eval_oracle(ch, vars) for ch in node[2]]
    if node[1] not in ORACLE:
        raise KeyError(f"no independent oracle for op {node[1]}")
    return ORACLE[node[1]](*vals)


# ---- native single-program packing (right-comb, with commutative reordering) ----
def pack(node):
    """Return (args, opcodes) if the tree is a right-comb of leaves (so the all-args-first core
    runs it as ONE program), else None. Uses commutativity to move a leaf to the left."""
    def collect(n):
        if n[0] == "num":
            return [n[1]], []
        if n[0] == "var":
            return None
        if n[0] != "op" or len(n[2]) != 2:        # only binary chains pack
            return None
        L, R = n[2]
        if L[0] == "num":
            left, rest = L[1], R
        elif R[0] == "num" and n[1] in COMMUTATIVE:
            left, rest = R[1], L
        else:
            return None
        sub = collect(rest)
        if sub is None:
            return None
        sub_args, sub_ops = sub
        return [left] + sub_args, sub_ops + [_NAME_TO_BYTE[n[1]]]
    return collect(node)


def compute(expr: str, vars: dict | None = None) -> dict:
    vars = vars or {}
    ast = parse(expr)
    rpn = to_rpn(ast)
    core = eval_core(ast, vars)
    try:
        oracle = eval_oracle(ast, vars)
        agree = abs(core - oracle) < 1e-9
    except KeyError as e:
        oracle, agree = f"({e})", None
    packed = pack(ast) if not vars else None      # pack only constant exprs in this demo
    native = None
    if packed:
        pargs, pops = packed
        nval = run_core(pops, pargs)
        native = {"args": pargs, "ops": [ca_word_for_opcode(b) for b in pops],
                  "value": nval, "matches": abs(nval - core) < 1e-9}
    return {"expr": expr, "rpn": rpn, "core": core, "oracle": oracle,
            "agree": agree, "native": native}


def _fmt_rpn(rpn):
    return " ".join(f"{x:g}" if isinstance(x, float) else str(x) for x in rpn)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("=== code in opcode: write an expression -> verified opcode program ===\n")
    cases = [
        ("(3+4)*2", None),
        ("3*(4+2)", None),
        ("1+2+3+4", None),
        ("(1+2)*(3+4)", None),      # NOT a right-comb -> composed verified ops
        ("clamp(9,1,5)", None),
        ("min(8, max(2,5))", None),
        ("(a+4)*2", {"a": 3.0}),    # with a variable
    ]
    ok = True
    for expr, vars in cases:
        r = compute(expr, vars)
        print(f"  {expr}{'  '+str(vars) if vars else ''}")
        print(f"    postfix opcode stream : {_fmt_rpn(r['rpn'])}")
        ag = {True: "agree", False: "DISAGREE", None: "no-oracle"}[r["agree"]]
        print(f"    core result {r['core']:g}  | independent oracle {r['oracle']}  -> {ag}")
        if r["native"]:
            n = r["native"]
            print(f"    native 1-program: args {[f'{a:g}' for a in n['args']]} "
                  f"ops {n['ops']} = {n['value']:g}  ({'matches' if n['matches'] else 'MISMATCH'})")
        else:
            print(f"    (not a right-comb -> ran as composed verified ops, one per node)")
        ok &= (r["agree"] in (True, None)) and (not r["native"] or r["native"]["matches"])
        print()

    print("  VERDICT:", "PASS -- every expression compiled to opcodes, executed on the real CA core,"
          if ok else "FAIL")
    print("           and agreed with an independent Python computation." if ok else "")
    print("  HONEST: postfix is the canonical opcode form; the core lacks literal-push/dup so it runs")
    print("          per-node or as a right-comb pack; agreement is evidence of correctness, not proof.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
