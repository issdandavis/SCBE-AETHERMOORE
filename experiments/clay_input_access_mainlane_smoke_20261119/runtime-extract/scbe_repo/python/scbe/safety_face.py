"""safety_face: an INDEPENDENT, sound-up-to-bound memory-safety analyzer as a verification face, plus a C
artifact + CBMC upgrade path (research wedge #2: "add a C face that runs a sound analyzer").

Wedge #1 (los_codegen_bench) showed example/property gates leave a residual: a candidate consistent with
every LOCAL check can still be wrong on the independent oracle (the circular-trust hole). The brief's answer
is a STRONGER FACE -- a sound analyzer whose verdict does not depend on the model. This module is that face
for the memory-safety properties that matter in flight C (out-of-bounds, divide-by-zero, integer overflow,
failed assertions).

WHAT "VERIFIED" HONESTLY MEANS HERE. The load-bearing, runnable-now analyzer is `check_bounded`: it
EXHAUSTIVELY enumerates the declared finite input domain and runs an instrumented interpreter that detects
each violation class. "SAFE" therefore means "no {OOB, div0, overflow, assert} violation exists over the
bounded input domain (N cases)" -- SOUND UP TO THAT BOUND, exactly CBMC's own caveat ("no violation up to
the unwinding bound"). It is NOT an unconditional proof, and it does not address the things that actually
dominate flight assurance (radiation/SEU, WCET, FDIR). consistency != correctness; bounded != unconditional.

THE CREDIBILITY JUMP over wedge #1's sampled gates: bounded checking is EXHAUSTIVE over the domain, so it
needs no luck -- it catches a bug that triggers at a single input value, which random/property sampling
misses with high probability (`sample_check` demonstrates the miss; `check_bounded` catches it for certain).

THE C FACE. `to_c` emits a CBMC-ready C harness (nondeterministic inputs + range assumptions + the body);
`check_cbmc` runs `cbmc` with --bounds-check/--div-by-zero-check/--signed-overflow-check WHEN cbmc is on
PATH, and honestly reports UNAVAILABLE otherwise (same graceful-skip idiom as loomfn's js/rust faces). C is
the flight-code language, so the C+CBMC path is the credibility bridge to a QUALIFIED EXTERNAL verifier --
the trusted base is the checker, the model is only the generator. The built-in checker and the C/CBMC face
check the SAME properties: OOB/div0/assert at any width, and overflow via --signed-overflow-check at width 32
and via explicit declared-width range asserts at width < 32 (so the faces AGREE on the shipped demos). Two
honest residual gaps, stated not glossed: (a) at width < 32 only assignment RESULTS carry the explicit width
assert, so overflow of an intermediate subexpression is caught by the built-in but not by cbmc; (b) Python
`//` floors where C `/` truncates on negative operands, so a divmod over signed inputs can diverge (`verify`
surfaces both as caveats; `to_c` emits a warning comment).

    PYTHONPATH=. python python/scbe/safety_face.py
"""

from __future__ import annotations

import itertools
import random
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# violation classes (the four a bounded model checker like CBMC finds on this subset)
OOB = "out-of-bounds"
DIV0 = "divide-by-zero"
OVERFLOW = "integer-overflow"
ASSERT = "assertion"

_ARITH = {"+", "-", "*"}  # overflow-checked at the declared width
_DIVMOD = {"//", "%"}  # divide-by-zero-checked
_CMP = {"==", "!=", "<", "<=", ">", ">="}  # yield 1/0


# ---- the safety IR (one IR -> the interpreter/checker AND the C face) -------------------------------------
@dataclass(frozen=True)
class Const:
    v: int


@dataclass(frozen=True)
class Var:  # a scalar local (also used for inputs)
    name: str


@dataclass(frozen=True)
class Get:  # array read arr[idx]
    arr: str
    idx: "Expr"


@dataclass(frozen=True)
class Bin:
    op: str
    a: "Expr"
    b: "Expr"


Expr = Union[Const, Var, Get, Bin]


@dataclass(frozen=True)
class Set:  # var = expr
    var: str
    expr: Expr


@dataclass(frozen=True)
class Put:  # arr[idx] = val
    arr: str
    idx: Expr
    val: Expr


@dataclass(frozen=True)
class Assert:  # the expr must be nonzero (true)
    expr: Expr


Stmt = Union[Set, Put, Assert]


@dataclass(frozen=True)
class Program:
    name: str
    inputs: Dict[str, Tuple[int, int]]  # input name -> inclusive (lo, hi) = the bound
    arrays: Dict[str, List[int]]  # array name -> initial contents (fixed size)
    body: List[Stmt]
    width: int = 32  # signed-integer width for the overflow check


@dataclass
class Violation:
    kind: str
    inputs: Dict[str, int]
    detail: str


class _Unsafe(Exception):
    def __init__(self, kind: str, detail: str):
        self.kind = kind
        self.detail = detail


# ---- the instrumented interpreter = the analyzer engine --------------------------------------------------
def _bounds(width: int) -> Tuple[int, int]:
    return -(1 << (width - 1)), (1 << (width - 1)) - 1


def _check_width(v: int, width: int, what: str) -> int:
    """Every VALUE in the program (input, constant, array element, arithmetic/divmod result, stored value)
    must fit the declared signed width -- else it overflows the type. Raising here is what makes the overflow
    class actually cover divmod (INT_MIN/-1) and out-of-width inputs/constants, not just +,-,* results."""
    lo, hi = _bounds(width)
    if v < lo or v > hi:
        raise _Unsafe(OVERFLOW, "%s = %d outside %d-bit signed [%d,%d]" % (what, v, width, lo, hi))
    return v


def _eval(e: Expr, env: Dict[str, int], arrays: Dict[str, List[int]], width: int) -> int:
    if isinstance(e, Const):
        return _check_width(e.v, width, "constant %d" % e.v)
    if isinstance(e, Var):
        return env[e.name]  # env values are width-checked at run start (inputs) / on assignment (Set results)
    if isinstance(e, Get):
        i = _eval(e.idx, env, arrays, width)
        a = arrays[e.arr]
        if i < 0 or i >= len(a):
            raise _Unsafe(OOB, "read %s[%d], size %d" % (e.arr, i, len(a)))
        return _check_width(a[i], width, "%s[%d]" % (e.arr, i))
    if isinstance(e, Bin):
        x = _eval(e.a, env, arrays, width)
        y = _eval(e.b, env, arrays, width)
        if e.op in _CMP:
            return 1 if {"==": x == y, "!=": x != y, "<": x < y, "<=": x <= y, ">": x > y, ">=": x >= y}[e.op] else 0
        if e.op in _DIVMOD:
            if y == 0:
                raise _Unsafe(DIV0, "%d %s 0" % (x, e.op))
            r = x // y if e.op == "//" else x % y
        else:
            r = {"+": x + y, "-": x - y, "*": x * y}[e.op]
        return _check_width(r, width, "%d %s %d" % (x, e.op, y))  # divmod AND arith results both width-checked
    raise TypeError("bad expr %r" % (e,))


def _run_once(prog: Program, env: Dict[str, int]) -> None:
    """Run the body on one concrete input assignment; raise _Unsafe on the first violation."""
    for nm, val in env.items():
        _check_width(val, prog.width, "input %s" % nm)  # an out-of-width input overflows the declared type
    arrays = {k: list(v) for k, v in prog.arrays.items()}  # fresh heap per run
    local = dict(env)
    for st in prog.body:
        if isinstance(st, Set):
            local[st.var] = _eval(st.expr, local, arrays, prog.width)
        elif isinstance(st, Put):
            i = _eval(st.idx, local, arrays, prog.width)
            if i < 0 or i >= len(arrays[st.arr]):
                raise _Unsafe(OOB, "write %s[%d], size %d" % (st.arr, i, len(arrays[st.arr])))
            arrays[st.arr][i] = _check_width(_eval(st.val, local, arrays, prog.width), prog.width, "stored value")
        elif isinstance(st, Assert):
            if _eval(st.expr, local, arrays, prog.width) == 0:
                raise _Unsafe(ASSERT, "assertion failed")


def validate(prog: Program) -> None:
    """Static reference check so a malformed Program raises a DEFINED ValueError instead of an uncaught
    KeyError escaping the analyzer mid-enumeration: every Var must be an input or assigned-before-use, and
    every array referenced must be declared."""
    defined = set(prog.inputs)

    def chk(e: Expr) -> None:
        if isinstance(e, Var):
            if e.name not in defined:
                raise ValueError("undefined variable %r" % e.name)
        elif isinstance(e, Get):
            if e.arr not in prog.arrays:
                raise ValueError("undefined array %r" % e.arr)
            chk(e.idx)
        elif isinstance(e, Bin):
            chk(e.a)
            chk(e.b)

    for st in prog.body:
        if isinstance(st, Set):
            chk(st.expr)
            defined.add(st.var)
        elif isinstance(st, Put):
            if st.arr not in prog.arrays:
                raise ValueError("undefined array %r" % st.arr)
            chk(st.idx)
            chk(st.val)
        elif isinstance(st, Assert):
            chk(st.expr)


def _domain_size(prog: Program) -> int:
    n = 1
    for lo, hi in prog.inputs.values():
        n *= max(0, hi - lo + 1)
    return n


MAX_BOUND = 5_000_000  # refuse to silently under-check a domain too large to enumerate


def check_bounded(prog: Program) -> Tuple[str, object]:
    """EXHAUSTIVELY enumerate the declared input domain. Returns ('SAFE', n_cases) if no violation exists
    over the bound, ('UNSAFE', Violation) at the first counterexample, ('BOUND_TOO_LARGE', n) if the domain
    exceeds MAX_BOUND, or ('EMPTY_DOMAIN', 0) if an input range is empty (honest: never silently 'SAFE' on a
    body that did not run). Raises ValueError on a malformed program (see validate)."""
    validate(prog)
    total = _domain_size(prog)
    if total == 0:
        return ("EMPTY_DOMAIN", 0)  # lo > hi somewhere; the body never executes -> not 'SAFE'
    if total > MAX_BOUND:
        return ("BOUND_TOO_LARGE", total)
    names = list(prog.inputs)
    ranges = [range(lo, hi + 1) for lo, hi in prog.inputs.values()]
    for combo in itertools.product(*ranges):
        env = dict(zip(names, combo))
        try:
            _run_once(prog, env)
        except _Unsafe as u:
            return ("UNSAFE", Violation(u.kind, env, u.detail))
    return ("SAFE", total)


def sample_check(prog: Program, n: int = 20, seed: int = 0) -> Optional[Violation]:
    """The WEAK face: try n random inputs (what sampled/property testing does). Returns the first violation
    found or None. Used only to demonstrate that sampling MISSES what bounded checking catches."""
    rng = random.Random(seed)
    for _ in range(n):
        env = {nm: rng.randint(lo, hi) for nm, (lo, hi) in prog.inputs.items()}
        try:
            _run_once(prog, env)
        except _Unsafe as u:
            return Violation(u.kind, env, u.detail)
    return None


# ---- the C face (flight-language artifact, gcc- and CBMC-compatible) -------------------------------------
_COP = {"//": "/", "%": "%"}  # C operator for divmod; arith/cmp tokens are identical


def _c_expr(e: Expr) -> str:
    if isinstance(e, Const):
        return str(e.v)
    if isinstance(e, Var):
        return e.name
    if isinstance(e, Get):
        return "%s[%s]" % (e.arr, _c_expr(e.idx))
    if isinstance(e, Bin):
        return "(%s %s %s)" % (_c_expr(e.a), _COP.get(e.op, e.op), _c_expr(e.b))
    raise TypeError("bad expr %r" % (e,))


def _c_vars(prog: Program) -> List[str]:
    return sorted({st.var for st in prog.body if isinstance(st, Set)})


def _has_divmod(prog: Program) -> bool:
    def walk(e: Expr) -> bool:
        if isinstance(e, Bin):
            return e.op in _DIVMOD or walk(e.a) or walk(e.b)
        if isinstance(e, Get):
            return walk(e.idx)
        return False

    for st in prog.body:
        exprs = [st.expr] if isinstance(st, Set) else [st.idx, st.val] if isinstance(st, Put) else [st.expr]
        if any(walk(e) for e in exprs):
            return True
    return False


def _maybe_negative(prog: Program) -> bool:
    return any(lo < 0 for lo, _ in prog.inputs.values()) or any(v < 0 for a in prog.arrays.values() for v in a)


def to_c(prog: Program) -> str:
    """Emit a CBMC-ready C harness: nondeterministic inputs constrained to the declared ranges, the body, and
    the user assertions. cbmc's --bounds-check / --div-by-zero-check / --signed-overflow-check handle OOB /
    div0 / 32-bit overflow. Because C `int` is 32-bit, a sub-32-bit declared `width` would NOT be checked by
    --signed-overflow-check alone, so for width < 32 we ALSO emit an explicit declared-width range assert on
    each assignment -- making cbmc check the SAME overflow property the built-in does (the faces agree on the
    shipped demos). Residual gap, stated not glossed: at width < 32 only assignment RESULTS get the explicit
    assert, so overflow of an intermediate subexpression is caught by the built-in but not by cbmc."""
    validate(prog)
    lo, hi = _bounds(prog.width)
    flags = "--bounds-check --div-by-zero-check --signed-overflow-check --unwind 1"
    lines = [
        "/* auto-generated safety harness for %s -- check with:" % prog.name,
        " *   cbmc %s.c %s */" % (prog.name, flags),
    ]
    if prog.width < 32:
        lines.append(
            "/* width=%d: explicit %d-bit range asserts make cbmc check the declared width (C int is 32-bit). */"
            % (prog.width, prog.width)
        )
    if _has_divmod(prog) and _maybe_negative(prog):
        lines.append(
            "/* WARNING: Python // floors but C / truncates toward zero; verdicts may differ for "
            "negative operands. */"
        )
    lines += [
        "#include <assert.h>",
        "#ifdef __CPROVER",
        "extern int nondet_int(void);",
        "#define ASSUME(c) __CPROVER_assume(c)",
        "#else",
        "#include <stdlib.h>",
        "static int nondet_int(void) { return rand(); }",
        "#define ASSUME(c) ((void)0)",
        "#endif",
        "",
        "int main(void) {",
    ]
    for nm, (ilo, ihi) in prog.inputs.items():
        lines.append("  int %s = nondet_int(); ASSUME(%d <= %s && %s <= %d);" % (nm, ilo, nm, nm, ihi))
    for nm, init in prog.arrays.items():
        lines.append("  int %s[%d] = {%s};" % (nm, len(init), ", ".join(str(x) for x in init)))
    for v in _c_vars(prog):
        lines.append("  int %s = 0;" % v)
    for st in prog.body:
        if isinstance(st, Set):
            lines.append("  %s = %s;" % (st.var, _c_expr(st.expr)))
            if prog.width < 32:
                lines.append(
                    "  assert(%d <= %s && %s <= %d);  /* %d-bit overflow */" % (lo, st.var, st.var, hi, prog.width)
                )
        elif isinstance(st, Put):
            lines.append("  %s[%s] = %s;" % (st.arr, _c_expr(st.idx), _c_expr(st.val)))
        elif isinstance(st, Assert):
            lines.append("  assert(%s);" % _c_expr(st.expr))
    lines += ["  return 0;", "}", ""]
    return "\n".join(lines)


def parse_cbmc(stdout: str) -> str:
    """Parse a cbmc run's verdict. SAFE on 'VERIFICATION SUCCESSFUL', UNSAFE on 'VERIFICATION FAILED'."""
    if "VERIFICATION SUCCESSFUL" in stdout:
        return "SAFE"
    if "VERIFICATION FAILED" in stdout:
        return "UNSAFE"
    return "UNKNOWN"


def check_cbmc(prog: Program, unwind: int = 4, timeout: int = 60) -> Tuple[str, str]:
    """Run cbmc on the emitted C WHEN it is on PATH (the qualified external verifier). Honest graceful-skip:
    returns ('UNAVAILABLE', reason) if cbmc is absent -- it never reports SAFE without actually running."""
    if shutil.which("cbmc") is None:
        return ("UNAVAILABLE", "cbmc not on PATH (install the free CBMC bounded model checker to enable)")
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / ("%s.c" % prog.name)
        f.write_text(to_c(prog), encoding="utf-8")
        cmd = [
            "cbmc",
            str(f),
            "--bounds-check",
            "--div-by-zero-check",
            "--signed-overflow-check",
            "--unwind",
            str(unwind),
        ]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:  # noqa: BLE001
            return ("ERROR", str(exc))
        return (parse_cbmc(out.stdout + out.stderr), " ".join(cmd))


def verify(prog: Program, unwind: int = 4) -> dict:
    """Combine the built-in bounded analyzer (always) with cbmc (when present) into one honest verdict."""
    status, evidence = check_bounded(prog)
    cbmc_status, cbmc_info = check_cbmc(prog, unwind=unwind)
    if status == "SAFE":
        verdict = "SAFE-UP-TO-BOUND (%d cases; no OOB/div0/overflow/assert)" % evidence
    elif status == "UNSAFE":
        verdict = "UNSAFE (%s)" % evidence.kind
    else:
        verdict = status
    if cbmc_status == "UNAVAILABLE":
        note = "cbmc not run (built-in is the analyzer; install cbmc to cross-validate the C face)"
    elif cbmc_status == status:
        note = "cross-validated by cbmc"
    else:
        note = "DISAGREEMENT: built-in=%s, cbmc=%s -- review" % (status, cbmc_status)
    caveats = []
    if prog.width < 32:
        caveats.append("width<%d: cbmc parity is per-assignment; intermediate-subexpr overflow is built-in-only" % 32)
    if _has_divmod(prog) and _maybe_negative(prog):
        caveats.append("//,% on negative operands: Python floors, C truncates -- faces may differ")
    return {
        "program": prog.name,
        "builtin": status,
        "builtin_evidence": evidence,
        "cbmc": cbmc_status,
        "cbmc_info": cbmc_info,
        "verdict": verdict,
        "note": note,
        "caveats": caveats,
    }


# ---- demo programs (each isolates one violation class; some safe, some buggy) -----------------------------
def _demo_programs() -> List[Tuple[str, Program]]:
    a5 = [10, 20, 30, 40, 50]
    return [
        ("safe_read", Program("safe_read", {"i": (0, 4)}, {"a": list(a5)}, [Set("r", Get("a", Var("i")))])),
        # off-by-one: i may reach 5 -> reads a[5] out of bounds
        ("oob_read", Program("oob_read", {"i": (0, 5)}, {"a": list(a5)}, [Set("r", Get("a", Var("i")))])),
        # divide by zero when d == 0
        ("div_bug", Program("div_bug", {"n": (1, 4), "d": (0, 3)}, {}, [Set("q", Bin("//", Var("n"), Var("d")))])),
        ("div_safe", Program("div_safe", {"n": (1, 4), "d": (1, 3)}, {}, [Set("q", Bin("//", Var("n"), Var("d")))])),
        # 8-bit signed overflow: a*b can exceed 127
        (
            "overflow_bug",
            Program(
                "overflow_bug", {"a": (0, 20), "b": (0, 20)}, {}, [Set("p", Bin("*", Var("a"), Var("b")))], width=8
            ),
        ),
        (
            "overflow_safe",
            Program(
                "overflow_safe", {"a": (0, 10), "b": (0, 10)}, {}, [Set("p", Bin("*", Var("a"), Var("b")))], width=8
            ),
        ),
        # assertion that does not hold for every input in range
        ("assert_fail", Program("assert_fail", {"x": (0, 9)}, {}, [Assert(Bin("<", Var("x"), Const(7)))])),
    ]


def _single_point_bug() -> Program:
    """A program whose ONLY unsafe input is x == 333 (the assertion fails there alone). Bounded checking
    finds it for certain; sampling a handful of the 0..499 inputs misses it with ~96% probability per run --
    the credibility jump from sampled to exhaustive."""
    return Program("needle", {"x": (0, 499)}, {}, [Assert(Bin("!=", Var("x"), Const(333)))])


def main() -> int:
    print("safety_face: independent sound-up-to-bound analyzer + C/CBMC face  (research wedge #2)\n")
    have_cbmc = shutil.which("cbmc") is not None
    print("  cbmc on PATH: %s%s\n" % (have_cbmc, "" if have_cbmc else "  (built-in checker still runs; C is emitted)"))
    print("  %-16s %-10s %s" % ("program", "builtin", "evidence / counterexample"))
    print("  " + "-" * 74)
    for _name, prog in _demo_programs():
        status, ev = check_bounded(prog)
        if status == "UNSAFE":
            shown = "%s at %s (%s)" % (ev.kind, ev.inputs, ev.detail)
        else:
            shown = "%s cases checked" % ev if status == "SAFE" else str(ev)
        print("  %-16s %-10s %s" % (prog.name, status, shown))

    print("\n  CREDIBILITY JUMP (exhaustive vs sampled), program 'needle' (only x==333 is unsafe):")
    needle = _single_point_bug()
    miss = sample_check(needle, n=20, seed=0)
    status, ev = check_bounded(needle)
    print("    sampled 20 inputs (the weak face): %s" % ("MISSED the bug" if miss is None else "hit %s" % miss.inputs))
    print(
        "    bounded exhaustive (this face):    %s%s"
        % (status, "" if status != "UNSAFE" else " -> %s at %s" % (ev.kind, ev.inputs))
    )

    print("\n  C face emitted for 'oob_read' (run `cbmc oob_read.c --bounds-check ...` to verify externally):")
    print("\n".join("    " + ln for ln in to_c(_demo_programs()[1][1]).splitlines()[:14]))
    print("\n  HONEST: 'SAFE' = no violation over the bounded domain (sound up to the bound), NOT an")
    print("          unconditional proof; radiation/WCET/FDIR are out of scope. The model only GENERATES;")
    print("          the analyzer (built-in, or cbmc) is the trusted, independent base.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
