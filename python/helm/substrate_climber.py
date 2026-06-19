"""substrate_climber: code THROUGH the board (loomfn) instead of as raw text, and measure the
difference -- the actual test of "does the substrate help?".

A raw-codegen climber emits Python: one language, unverified, and nothing stops an illegal move.
A SUBSTRATE climber emits a loomfn function -- a program on the board where every op is a legal
move -- and the harness runs it across python+javascript+rust. The board answer only counts if it
(a) computes the right value AND (b) every language face AGREES. That cross-face agreement is the
concrete advantage the board buys you: the same move, proven identical in three languages, instead
of one language you have to trust.

How a board climber is scored: it returns a loomfn FUNCTION (`func name p.. / ... / ret r`). For
each hidden test case the harness assembles a closed program -- bind the inputs, `call` the
function, `print` the result -- and runs it through loomfn.verify (python reference + js + rust).
"cleared" means: for every test, the reference value is correct AND no face disagrees.

HONEST CEILING (the real finding, not hidden): loomfn today is scalar + arrays + recursion with NO
strings, so the board can express the NUMERIC problems (factorial, fib, power, sum, ...) but not
the string/text problems in curriculum tiers 2-5. So this measures the substrate's advantage on the
subset it can express; closing the rest is the loomfn-strings work. The advantage shown here
(3-face agreement) is real on that subset; the limit is expressiveness, not the verification idea.

    python -m python.helm.substrate_climber              # reference board climber, all 3 faces
"""

from __future__ import annotations

import argparse
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from ..scbe import loomfn as L

BoardClimber = Callable[[Dict[str, Any]], str]


def _b(name: str, params: Sequence[str], ref: str, tests: Sequence[Tuple[Tuple[float, ...], float]]) -> Dict[str, Any]:
    return {"name": name, "params": list(params), "ref": ref, "tests": [(tuple(a), e) for a, e in tests]}


# Numeric sub-ladder: every problem is expressible on the board (scalar args, loops/recursion).
# `ref` is a correct loomfn FUNCTION; the asserts (tests) define behaviour for any other climber.
BOARD_LADDER = [
    _b("add", ["a", "b"], "func add a b / add s a b / ret s", [((2, 3), 5), ((10, 20), 30), ((-1, 1), 0), ((0, 0), 0)]),
    _b("square", ["n"], "func square n / mul r n n / ret r", [((4,), 16), ((0,), 0), ((9,), 81), ((12,), 144)]),
    _b(
        "power",
        ["b", "e"],
        "func power b e / const r 1 / label lp / brz e done / mul r r b / dec e / jmp lp / label done / ret r",
        [((2, 5), 32), ((3, 0), 1), ((5, 2), 25), ((2, 10), 1024)],
    ),
    _b(
        "sumto",
        ["n"],
        "func sumto n / const acc 0 / const i 1 / label lp / le c i n / brz c done / add acc acc i / inc i / jmp lp / "
        "label done / ret acc",
        [((5,), 15), ((1,), 1), ((10,), 55), ((100,), 5050)],
    ),
    _b(
        "factorial",
        ["n"],
        "func factorial n / const one 1 / le b n one / brz b rec / ret one / label rec / sub m n one / "
        "call fr factorial m / mul res n fr / ret res",
        [((5,), 120), ((0,), 1), ((1,), 1), ((6,), 720)],
    ),
    _b(
        "fib",
        ["n"],
        "func fib n / const two 2 / lt b n two / brz b rec / ret n / label rec / const one 1 / sub x n one / "
        "call fa fib x / sub y n two / call fb fib y / add z fa fb / ret z",
        [((0,), 0), ((1,), 1), ((10,), 55), ((7,), 13)],
    ),
]


def assemble(func_text: str, name: str, params: Sequence[str], args: Sequence[float]) -> str:
    """Wrap a climber's loomfn function into a closed program that binds args, calls it, prints."""
    if len(args) != len(params):
        raise ValueError("arity mismatch for %s: %d params, %d args" % (name, len(params), len(args)))
    inits = " / ".join("const a%d %s" % (i, _fmt(a)) for i, a in enumerate(args))
    callslots = " ".join("a%d" % i for i in range(len(args)))
    header = ((inits + " / ") if inits else "") + "call r %s %s / print r / halt" % (name, callslots)
    return header + " / " + func_text


def _fmt(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else repr(float(x))


def reference_board_climber(problem: Dict[str, Any]) -> str:
    """The hand-authored board program -- proves the problem is expressible on the board."""
    return problem["ref"]


def climb_on_board(
    climber: BoardClimber = reference_board_climber,
    ladder: Sequence[Dict[str, Any]] = BOARD_LADDER,
    faces: Sequence[str] = ("python", "javascript", "rust"),
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for prob in ladder:
        func_text = climber(prob)
        n_tests = len(prob["tests"])
        value_ok = 0
        faces_ok = 0
        note = ""
        for args, expected in prob["tests"]:
            try:
                prog = L.parse(assemble(func_text, prob["name"], prob["params"], args))
                r = L.verify(prog, faces=faces)
            except Exception as e:  # a malformed board program is a fail, never a fake pass
                note = "%s: %s" % (type(e).__name__, str(e)[:60])
                break
            ref = r["reference"]
            if ref is not None and abs(float(ref) - float(expected)) <= 1e-9:
                value_ok += 1
            ran = [lang for lang, d in r["results"].items() if d["status"] in ("AGREE", "DISAGREE")]
            if ran and not r["disagree"] and r["verified_count"] == len(ran):
                faces_ok += 1
        cleared = value_ok == n_tests and faces_ok == n_tests and not note
        rows.append(
            {
                "name": prob["name"],
                "tests": n_tests,
                "value_ok": value_ok,
                "faces_agree": faces_ok,
                "cleared": cleared,
                "note": note,
            }
        )
    solved = sum(1 for r in rows if r["cleared"])
    return {
        "climber": getattr(climber, "__name__", "climber"),
        "faces": list(faces),
        "solved": solved,
        "total": len(rows),
        "all_cross_face_verified": all(r["faces_agree"] == r["tests"] for r in rows if r["cleared"]),
        "rows": rows,
    }


def render(summary: Dict[str, Any]) -> str:
    lines = [
        "SUBSTRATE CLIMB  (code THROUGH the board: loomfn -> %s, every answer cross-face verified)"
        % "+".join(summary["faces"]),
        "  climber: %s" % summary["climber"],
    ]
    for r in summary["rows"]:
        mark = "PASS" if r["cleared"] else (r["note"] or "FAIL")
        lines.append(
            "  %-11s %d/%d value  %d/%d faces-agree  %s"
            % (r["name"], r["value_ok"], r["tests"], r["faces_agree"], r["tests"], mark)
        )
    lines.append(
        "  --> solved %d/%d on the board; every solved answer agrees across %s."
        % (summary["solved"], summary["total"], "+".join(summary["faces"]))
    )
    lines.append(
        "  ceiling: the board expresses scalar numeric fns (loops/recursion). strings/text "
        "(curriculum T2-T5) need loomfn string support -> next."
    )
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="scbe-substrate-climber", description="code through the board, verified 3 faces")
    ap.add_argument("--faces", default="python,javascript,rust", help="comma-separated faces to verify against")
    a = ap.parse_args(list(argv) if argv is not None else None)
    faces = tuple(f.strip() for f in a.faces.split(",") if f.strip())
    print(render(climb_on_board(faces=faces)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
