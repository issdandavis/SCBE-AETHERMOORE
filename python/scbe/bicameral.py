"""
Bicameral cognition — two hemispheres run one program, then reconcile.
======================================================================

A bifurcated internal thought process over a cube program:

  LOGIC hemisphere     — the exact opcode VM. Slow-but-right (System 2).
  INTUITION hemisphere — a fast surrogate VM that FUDGES the hard nonlinear ops
                         (sqrt≈half, pow≈multiply, rounding≈ignore). It hallucinates
                         the result without doing the hard math (System 1).

The corpus callosum (`reconcile`) then SEES THE RELATION between the two answers and
INTERPRETS it: an exact match means the program was intuitive; a divergence is
*localized* to exactly the nonlinear ops the intuition skipped. So the system doesn't
just get an answer — it knows how much to trust its gut, and why.

This is the dual-process core a "pure-AI-OS" needs: every computation carries both its
logical truth and its intuitive guess, and the gap between them is a usable signal.
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

from . import polyglot as P


def _safe_div(a, b):
    return a / b if b != 0 else 0.0


def _safe_mod(a, b):
    return math.fmod(a, b) if b != 0 else 0.0


def _safe_sqrt(a):
    return math.sqrt(a) if a >= 0 else 0.0


# exact op table — matches polyglot's safe-mode semantics (roundabouts on ÷0/√-)
EXACT: Dict[str, Tuple[int, object]] = {
    "add": (2, lambda a, b: a + b),
    "sub": (2, lambda a, b: a - b),
    "mul": (2, lambda a, b: a * b),
    "div": (2, _safe_div),
    "eq": (2, lambda a, b: 1.0 if a == b else 0.0),
    "neq": (2, lambda a, b: 1.0 if a != b else 0.0),
    "lt": (2, lambda a, b: 1.0 if a < b else 0.0),
    "lte": (2, lambda a, b: 1.0 if a <= b else 0.0),
    "gt": (2, lambda a, b: 1.0 if a > b else 0.0),
    "gte": (2, lambda a, b: 1.0 if a >= b else 0.0),
    "pow": (2, lambda a, b: a**b),
    "min": (2, min),
    "max": (2, max),
    "mod": (2, _safe_mod),
    "neg": (1, lambda a: -a),
    "abs": (1, abs),
    "sqrt": (1, _safe_sqrt),
    "floor": (1, lambda a: float(math.floor(a))),
    "ceil": (1, lambda a: float(math.ceil(a))),
    "round": (1, lambda a: float(round(a))),
    "inc": (1, lambda a: a + 1),
    "dec": (1, lambda a: a - 1),
}

# the ops intuition can't do in its head — it fudges these
NONLINEAR = {"sqrt", "pow", "floor", "ceil", "round"}
INTUIT: Dict[str, Tuple[int, object]] = dict(EXACT)
INTUIT["sqrt"] = (1, lambda a: a * 0.5 + 1.0)  # "about half"
INTUIT["pow"] = (2, lambda a, b: a * b)  # "multiply, close enough"
INTUIT["floor"] = (1, lambda a: a)  # ignore the rounding
INTUIT["ceil"] = (1, lambda a: a)
INTUIT["round"] = (1, lambda a: a)


def _run(prog: Sequence[int], table) -> Tuple[object, List[str]]:
    """Stack VM over an op table (pop b then a, like the polyglot faces)."""
    s: List[float] = [2.0, 3.0, 4.0]
    used_nonlinear: List[str] = []
    for b in prog:
        name = P.BYTE_TO_NAME[b]
        arity, fn = table[name]
        if name in NONLINEAR:
            used_nonlinear.append(name)
        try:
            if arity == 2:
                y = s.pop()
                x = s.pop()
                s.append(fn(x, y))
            else:
                x = s.pop()
                s.append(fn(x))
        except (IndexError, OverflowError, ValueError, ZeroDivisionError):
            return None, used_nonlinear  # underflow / blew up -> incomplete
    return (s[-1] if s else None), used_nonlinear


def logic(prog: Sequence[int]) -> object:
    """The exact hemisphere."""
    return _run(prog, EXACT)[0]


def intuition(prog: Sequence[int]) -> Tuple[object, List[str]]:
    """The fast/fudged hemisphere — returns (guess, nonlinear ops it skipped)."""
    return _run(prog, INTUIT)


def reconcile(truth: object, guess: object, nonlinear: Sequence[str]) -> Dict[str, object]:
    """See the relation between the two hemispheres and interpret it."""
    out: Dict[str, object] = {"logic": truth, "intuition": guess, "nonlinear_ops": sorted(set(nonlinear))}
    if truth is None or guess is None:
        out.update(
            relation="incomplete",
            confidence=0.0,
            interpretation="a hemisphere couldn't finish (underflow/overflow) — no reconciliation",
        )
        return out
    err = abs(truth - guess)
    rel = err / max(abs(truth), 1e-9)
    out["abs_error"], out["rel_error"] = err, rel
    if err < 1e-6:
        rel_class = "exact match"
    elif (truth < 0) != (guess < 0) and abs(truth) > 1e-9:
        rel_class = "sign flip"
    elif rel < 0.10:
        rel_class = "close"
    else:
        rel_class = "diverged"
    out["relation"] = rel_class
    out["confidence"] = round(max(0.0, 1.0 - rel), 3)
    if rel_class == "exact match":
        out["interpretation"] = "intuition nailed it — this program is intuitive (no hard nonlinearity, or it cancels)"
    elif not out["nonlinear_ops"]:
        out["interpretation"] = "diverged with NO nonlinear ops — anomaly, both should agree (investigate)"
    else:
        out["interpretation"] = "intuition %s; the gap localizes to the nonlinear op(s): %s" % (
            rel_class,
            ", ".join(out["nonlinear_ops"]),
        )
    return out


def think(prog: Sequence[int]) -> Dict[str, object]:
    """Run both hemispheres and reconcile — one bicameral thought."""
    truth = logic(prog)
    guess, nonlinear = intuition(prog)
    return reconcile(truth, guess, nonlinear)


def _fmt(v) -> str:
    return "incomplete" if v is None else ("%.4g" % v if isinstance(v, float) else str(v))


def render(prog: Sequence[int]) -> str:
    t = think(prog)
    lines = [
        "  logic     %s" % _fmt(t["logic"]),
        "  intuition %s" % _fmt(t["intuition"]),
        "  relation  %s   (confidence %.0f%%)" % (t["relation"], 100 * float(t.get("confidence", 0.0))),
        "  -> %s" % t["interpretation"],
    ]
    return "\n".join(lines)


def _demo() -> None:
    from . import polyglot as PG

    print("Bicameral cognition — logic vs intuition, reconciled\n")
    for ops in (["add", "mul", "inc"], ["add", "sqrt", "mul"], ["mul", "pow"], ["add", "div"]):
        print(" ".join(ops) + ":")
        print(render(PG.program_bytes(*ops)), "\n")


if __name__ == "__main__":
    _demo()
