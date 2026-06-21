"""self_repair_harness: run a staged retry-loop eval, emit the staged jsonl, measure recovery LIFT.

Closes the loop harness -> jsonl -> staged_retry_score. A (pluggable) GENERATOR produces a first attempt; if
it fails the PUBLIC tests the agent knows it failed and a (pluggable) REPAIR step retries; the HIDDEN oracle
judges. Each problem becomes one staged record (the four stages) that staged_retry_score consumes, so the
becoming metric falls out intrinsically:

    recovery_lift = FIX_SOLVED / total   (problems the repair loop converted, over the SAME first attempts)

That is a FAIR baseline by construction: the lift is exactly the gap between first-try solving and
after-repair solving on identical attempts -- no separate control run, no menu-elimination ([[tool-use-is-
the-skill]]). The PUBLIC_PASS_HIDDEN_FAIL stage is the overfit/circular-trust residual (a stronger local
face -- safety_face -- would convert some of those into retries).

A deterministic reference generator/repair prove the instrument end-to-end ($0, no model). Swap in an ollama
generator + an error-reprompt repair for real numbers ([[verified-trajectory-training]] / train-on-becoming).
The reference repair is IDEALIZED (it fixes every recoverable miss) -- this measures the HARNESS, not a
capability; a real model's repair will not always succeed, and the harness will show that honestly.

    python -m python.helm.self_repair_harness
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from . import staged_retry_score as srs
from .self_repair_corpus import runs_ok

Generator = Callable[[Dict[str, Any], int], str]  # (problem, attempt_index) -> code
Repair = Callable[[Dict[str, Any], str, str], str]  # (problem, failing_code, fail_msg) -> code


def _all_pass(code: str, asserts: Sequence[str]) -> bool:
    return all(runs_ok(code, a)[0] for a in asserts)


def _first_fail(code: str, asserts: Sequence[str]) -> str:
    for a in asserts:
        ok, msg = runs_ok(code, a)
        if not ok:
            return msg or "AssertionError"
    return ""


def run_problem(problem: Dict[str, Any], generator: Generator, repair: Optional[Repair]) -> Dict[str, Any]:
    """Run one problem through the staged retry loop; return a staged record (staged_retry_score schema)."""
    public = problem.get("public", [])
    hidden = problem.get("hidden", [])
    code = generator(problem, 0)
    first_public = _all_pass(code, public)
    first_hidden = _all_pass(code, hidden)
    rec = {
        "task_id": problem.get("task_id"),
        "first_try_public_pass": first_public,
        "first_try_hidden_pass": first_hidden,
        "retried": False,
        "retry_hidden_pass": False,
    }
    if first_hidden:
        rec["category"] = srs.SOLVED_FIRST_TRY
        return rec
    if first_public:  # passed the visible tests -> the agent thinks it is done, never retries
        rec["category"] = srs.PUBLIC_PASS_HIDDEN_FAIL
        return rec
    # public failed -> the agent knows it failed -> repair (if a repair step is provided)
    if repair is None:
        rec["category"] = srs.FIX_FAILED  # baseline: no repair available
        return rec
    fixed = repair(problem, code, _first_fail(code, public))
    retry_hidden = _all_pass(fixed, hidden)
    rec.update(retried=True, retry_hidden_pass=retry_hidden)
    rec["category"] = srs.FIX_SOLVED if retry_hidden else srs.FIX_FAILED
    return rec


def run_staged(problems: Sequence[Dict[str, Any]], generator: Generator, repair: Optional[Repair]) -> List[Dict]:
    return [run_problem(p, generator, repair) for p in problems]


def recovery_lift(records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """The becoming metric: first-try solve rate vs after-repair solve rate, on the SAME attempts."""
    s = srs.score(records)
    total = s["total"] or 1
    first_try = s["counts"][srs.SOLVED_FIRST_TRY] / total
    with_repair = (s["counts"][srs.SOLVED_FIRST_TRY] + s["counts"][srs.FIX_SOLVED]) / total
    return {
        "first_try_solve_rate": round(first_try, 3),
        "with_repair_solve_rate": round(with_repair, 3),
        "recovery_lift": round(with_repair - first_try, 3),  # == FIX_SOLVED / total
        "repair_conversion": s["repair_conversion"],
        "overfit_no_retry_rate": s["overfit_no_retry_rate"],
    }


# ---- a deterministic REFERENCE instrument (proves the harness; $0, no model) ------------------------------
def _ref_problems() -> List[Dict[str, Any]]:
    p = [
        {
            "task_id": "add",
            "good": "def f(a,b):\n    return a+b",
            "public": ["assert f(2,3)==5"],
            "hidden": ["assert f(-1,1)==0", "assert f(10,20)==30"],
        },
        {
            "task_id": "maxof",
            "good": "def f(a,b):\n    return a if a>b else b",
            "public": ["assert f(1,2)==2"],
            "hidden": ["assert f(5,3)==5", "assert f(-1,-2)==-1"],
        },
        {
            "task_id": "evens",
            "good": "def f(xs):\n    return [x for x in xs if x%2==0]",
            "public": ["assert f([1,2,3,4])==[2,4]"],
            "hidden": ["assert f([0,1])==[0]", "assert f([])==[]"],
        },
        {
            "task_id": "rev",
            "good": "def f(s):\n    return s[::-1]",
            "public": ["assert f('ab')=='ba'"],
            "hidden": ["assert f('')==''", "assert f('xyz')=='zyx'"],
        },
        {
            "task_id": "sub",
            "good": "def f(a,b):\n    return a-b",
            "public": ["assert f(5,2)==3"],
            "hidden": ["assert f(0,4)==-4", "assert f(9,9)==0"],
        },
        {
            "task_id": "minof",
            "good": "def f(a,b):\n    return a if a<b else b",
            "public": ["assert f(1,2)==1"],
            "hidden": ["assert f(5,3)==3", "assert f(-1,-2)==-2"],
        },
        {
            "task_id": "count_pos",
            "good": "def f(xs):\n    return sum(1 for x in xs if x>0)",
            "public": ["assert f([1,-2,3])==2"],
            "hidden": ["assert f([0,0])==0", "assert f([-5,5])==1"],
        },
        {
            "task_id": "is_even",
            "good": "def f(n):\n    return n%2==0",
            "public": ["assert f(4)==True"],
            "hidden": ["assert f(3)==False", "assert f(0)==True"],
        },
        {
            "task_id": "double",
            "good": "def f(x):\n    return x*2",
            "public": ["assert f(3)==6"],
            "hidden": ["assert f(0)==0", "assert f(-2)==-4"],
        },
        {
            "task_id": "last",
            "good": "def f(xs):\n    return xs[-1] if xs else 0",
            "public": ["assert f([1,2,3])==3"],
            "hidden": ["assert f([5])==5", "assert f([])==0"],
        },
        {
            "task_id": "absval",
            "good": "def f(x):\n    return x if x>=0 else -x",
            "public": ["assert f(-4)==4"],
            "hidden": ["assert f(4)==4", "assert f(0)==0"],
        },
        {
            "task_id": "concat",
            "good": "def f(a,b):\n    return a+b",
            "public": ["assert f('a','b')=='ab'"],
            "hidden": ["assert f('','x')=='x'", "assert f('xy','z')=='xyz'"],
        },
    ]
    return p


def _ref_generator(weights=(0.5, 0.3, 0.2)) -> Generator:
    """Flaky onboard model: correct / wrong-public (fails the visible test, recoverable) / wrong-overfit
    (passes public via a memorized special-case, fails hidden). Seeded per task -> reproducible."""

    def gen(problem: Dict[str, Any], attempt: int) -> str:
        rng = random.Random("%s-%d" % (problem["task_id"], attempt))
        r = rng.random()
        good = problem["good"]
        if r < weights[0]:
            return good
        if r < weights[0] + weights[1]:
            return "def f(*a):\n    return None"  # wrong, fails the public test (the agent will know)
        # wrong-overfit: hard-code the public example's answer, wrong in general
        pub = problem["public"][0]
        return "def f(*a):\n    return %s" % pub.split("==", 1)[1].strip()

    return gen


def _ref_repair() -> Repair:
    """Idealized repair: returns the known-good code. Measures the harness, NOT model capability."""

    def repair(problem: Dict[str, Any], code: str, fail_msg: str) -> str:
        return problem["good"]

    return repair


def write_jsonl(path: str, records: Sequence[Dict]) -> None:
    Path(path).write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="run a staged retry-loop eval, emit the staged jsonl, report lift")
    ap.add_argument("--out", default=None, help="write the staged jsonl here (feeds staged_retry_score)")
    a = ap.parse_args(argv)
    problems = _ref_problems()
    records = run_staged(problems, _ref_generator(), _ref_repair())
    print(srs.render(srs.score(records)))
    lift = recovery_lift(records)
    print(
        "\n  recovery_lift: first-try %.3f -> with-repair %.3f  (= %+.3f, the becoming metric)"
        % (lift["first_try_solve_rate"], lift["with_repair_solve_rate"], lift["recovery_lift"])
    )
    print("  NOTE: reference repair is idealized (fixes every recoverable miss) -> this validates the INSTRUMENT;")
    print("        swap in a real model+repair for a capability number. The PUBLIC_PASS_HIDDEN_FAIL bucket is")
    print("        the overfit residual a stronger local face (safety_face) would convert to retries.")
    if a.out:
        write_jsonl(a.out, records)
        print(
            "\n  wrote %d staged records -> %s  (run: python -m python.helm.staged_retry_score %s)"
            % (len(records), a.out, a.out)
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
